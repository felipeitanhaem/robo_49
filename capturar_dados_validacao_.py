# capturar_dados_validacao.py
"""
Capturador de Dados para Validação de Estratégia
Volume + Cruzamento RSI/MA_RSI + Cor da Vela

Este script:
1. Coleta candles históricos do MT5 (30min por padrão)
2. Calcula RSI, MA do RSI e volume médio
3. Detecta cada cruzamento e verifica se houve pico de volume
4. Mede o que aconteceu DEPOIS do sinal (acerto/erro)
5. Salva em CSV e JSON para calibração posterior
6. Exibe estatísticas resumidas

Uso:
    python capturar_dados_validacao.py
    python capturar_dados_validacao.py --ativo VALE3 --timeframe 30 --candles 2000
    python capturar_dados_validacao.py --ativo VALE3 PETR4 ITUB4 --timeframe 30 --candles 1500
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import os
import argparse
from datetime import datetime


# ============================================================
# CONFIGURAÇÕES PADRÃO
# ============================================================

TIMEFRAMES = {
    "1": mt5.TIMEFRAME_M1,
    "2": mt5.TIMEFRAME_M2,
    "5": mt5.TIMEFRAME_M5,
    "15": mt5.TIMEFRAME_M15,
    "30": mt5.TIMEFRAME_M30,
    "60": mt5.TIMEFRAME_H1,
    "240": mt5.TIMEFRAME_H4,
    "D": mt5.TIMEFRAME_D1,
}

# Parâmetros de detecção (podem ser ajustados depois na calibração)
RSI_PERIOD_PADRAO = 5
MA_PERIOD_PADRAO = 9
VOLUME_LOOKBACK_PADRAO = 20
VOLUME_FATOR_PADRAO = 1.5

# Horizonte de validação: quantas velas à frente olhar para ver se acertou
HORIZONTE_VALIDACAO = [1, 3, 5, 10]  # mede o que aconteceu em 1, 3, 5 e 10 velas à frente


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def calculate_rsi(series, period=5):
    """Calcula o RSI usando método Wilder (igual ao MT5)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def cor_vela(row):
    """Retorna a cor da vela."""
    if row['close'] > row['open']:
        return 'VERDE'
    elif row['close'] < row['open']:
        return 'VERMELHA'
    return 'NEUTRA'


def obter_candles(symbol, timeframe, quantidade):
    """Obtém candles do MT5 como DataFrame."""
    if not mt5.symbol_select(symbol, True):
        print(f"⚠️ Não foi possível selecionar {symbol}")
        return None
    
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, quantidade)
    if rates is None or len(rates) == 0:
        print(f"⚠️ Sem dados para {symbol}")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


# ============================================================
# ENRIQUECIMENTO DOS DADOS
# ============================================================

def enriquecer_dataframe(df, rsi_period, ma_period, volume_lookback):
    """
    Adiciona colunas calculadas ao DataFrame.
    """
    df = df.copy()
    
    # --- RSI ---
    df['rsi'] = calculate_rsi(df['close'], period=rsi_period)
    df['ma_rsi'] = df['rsi'].rolling(window=ma_period).mean()
    
    # --- Volume ---
    df['volume_medio'] = df['tick_volume'].shift(1).rolling(window=volume_lookback).mean()
    df['volume_ratio'] = df['tick_volume'] / df['volume_medio'].replace(0, np.nan)
    
    # --- Cor ---
    df['cor'] = df.apply(cor_vela, axis=1)
    
    # --- Cruzamentos do RSI (CORRIGIDO) ---
    # Garante booleano estrito (sem NaN) antes de fazer operações lógicas
    df['rsi_acima_ma'] = (df['rsi'] > df['ma_rsi']).astype('boolean')
    df['rsi_acima_ma_ant'] = df['rsi_acima_ma'].shift(1).fillna(False).astype('boolean')
    
    # Cruzamento para ALTA: agora True, antes False
    mask_alta = (df['rsi_acima_ma'] == True) & (df['rsi_acima_ma_ant'] == False)
    
    # Cruzamento para BAIXA: agora False, antes True
    mask_baixa = (df['rsi_acima_ma'] == False) & (df['rsi_acima_ma_ant'] == True)
    
    # Monta coluna de cruzamento
    df['cruzamento'] = None
    df.loc[mask_alta, 'cruzamento'] = 'ALTA'
    df.loc[mask_baixa, 'cruzamento'] = 'BAIXA'
    df['houve_cruzamento'] = df['cruzamento'].notna()
    
    # --- Pico de volume ---
    df['pico_volume_atual'] = df['volume_ratio'] >= VOLUME_FATOR_PADRAO
    df['pico_volume_anterior'] = df['pico_volume_atual'].shift(1).fillna(False)
    
    # --- Tamanhos ---
    df['corpo'] = (df['close'] - df['open']).abs()
    df['corpo_pct'] = (df['corpo'] / df['open']) * 100
    df['range_pct'] = ((df['high'] - df['low']) / df['open']) * 100
    
    df['pavio_sup'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['pavio_inf'] = df[['open', 'close']].min(axis=1) - df['low']
    df['pavio_sup_pct'] = (df['pavio_sup'] / df['open']) * 100
    df['pavio_inf_pct'] = (df['pavio_inf'] / df['open']) * 100
    
    # --- Direção do candle ---
    df['direcao'] = np.where(df['close'] > df['open'], 1,
                     np.where(df['close'] < df['open'], -1, 0))
    
    return df




# ============================================================
# VALIDAÇÃO: O QUE ACONTECEU DEPOIS?
# ============================================================

def adicionar_retornos_futuros(df, horizontes=[1, 3, 5, 10]):
    """
    Adiciona colunas com o retorno futuro em N velas à frente.
    Ex: retorno_5 = (close[t+5] - close[t]) / close[t] * 100
    """
    df = df.copy()
    for h in horizontes:
        df[f'retorno_{h}'] = ((df['close'].shift(-h) - df['close']) / df['close']) * 100
        df[f'max_futuro_{h}'] = (
            (df['high'].shift(-h).rolling(h).max() if h > 1 else df['high'].shift(-h))
            - df['close']
        ) / df['close'] * 100
        df[f'min_futuro_{h}'] = (
            (df['low'].shift(-h).rolling(h).min() if h > 1 else df['low'].shift(-h))
            - df['close']
        ) / df['close'] * 100
    return df


def validar_sinal(row, sinal):
    """
    Dado um sinal ('COMPRA' ou 'VENDA'), verifica se o mercado foi nessa direção.
    Retorna um dict com os resultados em cada horizonte.
    """
    resultado = {}
    for h in HORIZONTE_VALIDACAO:
        retorno = row.get(f'retorno_{h}', np.nan)
        max_fut = row.get(f'max_futuro_{h}', np.nan)
        min_fut = row.get(f'min_futuro_{h}', np.nan)
        
        if pd.isna(retorno):
            resultado[f'acerto_{h}'] = None
            resultado[f'retorno_{h}_val'] = None
            continue
        
        if sinal == 'COMPRA':
            # Acerto = retorno positivo
            resultado[f'acerto_{h}'] = bool(retorno > 0)
            resultado[f'retorno_{h}_val'] = round(retorno, 3)
            # Melhor caso = max_futuro, pior caso = min_futuro
            resultado[f'ganho_max_{h}'] = round(max_fut, 3)
            resultado[f'perda_max_{h}'] = round(min_fut, 3)
        elif sinal == 'VENDA':
            # Acerto = retorno negativo
            resultado[f'acerto_{h}'] = bool(retorno < 0)
            resultado[f'retorno_{h}_val'] = round(retorno, 3)
            # Melhor caso = min_futuro (queda), pior caso = max_futuro (subida)
            resultado[f'ganho_max_{h}'] = round(-min_fut, 3)  # positivo = ganhou
            resultado[f'perda_max_{h}'] = round(-max_fut, 3)  # negativo = perdeu
        else:
            resultado[f'acerto_{h}'] = None
            resultado[f'retorno_{h}_val'] = None
    
    return resultado


# ============================================================
# COLETA PRINCIPAL
# ============================================================

def coletar_dados_ativo(
    symbol,
    timeframe_str="30",
    quantidade=2000,
    rsi_period=RSI_PERIOD_PADRAO,
    ma_period=MA_PERIOD_PADRAO,
    volume_lookback=VOLUME_LOOKBACK_PADRAO,
):
    """
    Coleta e enriquece dados de um ativo.
    Retorna um DataFrame pronto para análise.
    """
    timeframe = TIMEFRAMES.get(timeframe_str)
    if timeframe is None:
        print(f"❌ Timeframe inválido: {timeframe_str}")
        return None
    
    print(f"\n📊 Coletando {symbol} ({timeframe_str}min, {quantidade} candles)...")
    
    df = obter_candles(symbol, timeframe, quantidade)
    if df is None:
        return None
    
    print(f"   ✅ {len(df)} candles coletados")
    print(f"   📅 De {df['time'].iloc[0]} a {df['time'].iloc[-1]}")
    
    # Enriquece com indicadores
    df = enriquecer_dataframe(df, rsi_period, ma_period, volume_lookback)
    
    # Adiciona retornos futuros
    df = adicionar_retornos_futuros(df, HORIZONTE_VALIDACAO)
    
    df['symbol'] = symbol
    df['timeframe'] = timeframe_str
    df['rsi_period'] = rsi_period
    df['ma_period'] = ma_period
    df['volume_lookback'] = volume_lookback
    
    return df


# ============================================================
# DETECÇÃO DE SINAIS
# ============================================================

def detectar_sinais(df, volume_fator=VOLUME_FATOR_PADRAO):
    """
    Detecta os sinais de confluência (Volume + Cruzamento RSI + Cor da Vela).
    Retorna um DataFrame apenas com as linhas onde houve sinal.
    """
    df = df.copy()
    
    # Reconstrói o pico de volume com o fator passado
    df['pico_volume_atual'] = df['volume_ratio'] >= volume_fator
    df['pico_volume_anterior'] = df['pico_volume_atual'].shift(1).fillna(False)
    df['pico_em_algum'] = df['pico_volume_atual'] | df['pico_volume_anterior']
    
    # Sinal
    df['sinal'] = 'N'
    
    # COMPRA: cruzamento ALTA + pico em algum + vela verde
    mask_compra = (
        (df['cruzamento'] == 'ALTA') &
        (df['pico_em_algum']) &
        (df['cor'] == 'VERDE')
    )
    df.loc[mask_compra, 'sinal'] = 'COMPRA'
    
    # VENDA: cruzamento BAIXA + pico em algum + vela vermelha
    mask_venda = (
        (df['cruzamento'] == 'BAIXA') &
        (df['pico_em_algum']) &
        (df['cor'] == 'VERMELHA')
    )
    df.loc[mask_venda, 'sinal'] = 'VENDA'
    
    return df


def extrair_sinais_com_validacao(df, volume_fator=VOLUME_FATOR_PADRAO):
    """
    Extrai apenas os sinais e valida o que aconteceu depois de cada um.
    Retorna um DataFrame com os sinais e suas métricas de acerto.
    """
    df = detectar_sinais(df, volume_fator)
    
    # Filtra apenas onde houve sinal
    sinais = df[df['sinal'].isin(['COMPRA', 'VENDA'])].copy()
    
    if len(sinais) == 0:
        return pd.DataFrame()
    
    # Valida cada sinal
    for i, row in sinais.iterrows():
        validacao = validar_sinal(row, row['sinal'])
        for k, v in validacao.items():
            sinais.at[i, k] = v
    
    # Colunas finais organizadas
    colunas_finais = [
        'symbol', 'timeframe', 'time', 'open', 'high', 'low', 'close',
        'tick_volume', 'volume_medio', 'volume_ratio',
        'rsi', 'ma_rsi', 'cruzamento', 'cor',
        'corpo_pct', 'range_pct', 'pavio_sup_pct', 'pavio_inf_pct',
        'pico_volume_atual', 'pico_volume_anterior',
        'sinal',
    ]
    # Adiciona colunas de retorno/acerto
    for h in HORIZONTE_VALIDACAO:
        colunas_finais.extend([
            f'retorno_{h}_val', f'acerto_{h}',
            f'ganho_max_{h}', f'perda_max_{h}'
        ])
    
    colunas_existentes = [c for c in colunas_finais if c in sinais.columns]
    sinais = sinais[colunas_existentes]
    
    # Renomeia colunas de validação para ficar mais legível
    rename_map = {}
    for h in HORIZONTE_VALIDACAO:
        rename_map[f'retorno_{h}_val'] = f'retorno_{h}v'
        rename_map[f'acerto_{h}'] = f'acerto_{h}v'
        rename_map[f'ganho_max_{h}'] = f'ganho_max_{h}v'
        rename_map[f'perda_max_{h}'] = f'perda_max_{h}v'
    sinais = sinais.rename(columns=rename_map)
    
    return sinais


# ============================================================
# ESTATÍSTICAS
# ============================================================

def gerar_estatisticas(sinais):
    """Gera um resumo estatístico dos sinais detectados."""
    if len(sinais) == 0:
        return {'total_sinais': 0}
    
    stats = {
        'total_sinais': len(sinais),
        'por_tipo': {},
        'por_horizonte': {},
    }
    
    for sinal_tipo in ['COMPRA', 'VENDA']:
        subset = sinais[sinais['sinal'] == sinal_tipo]
        if len(subset) == 0:
            continue
        
        stats['por_tipo'][sinal_tipo] = {
            'quantidade': len(subset),
            'retorno_medio_1v': round(subset['retorno_1v'].mean(), 3) if 'retorno_1v' in subset else None,
            'retorno_medio_3v': round(subset['retorno_3v'].mean(), 3) if 'retorno_3v' in subset else None,
            'retorno_medio_5v': round(subset['retorno_5v'].mean(), 3) if 'retorno_5v' in subset else None,
            'retorno_medio_10v': round(subset['retorno_10v'].mean(), 3) if 'retorno_10v' in subset else None,
            'taxa_acerto_1v': round(subset['acerto_1v'].mean() * 100, 1) if 'acerto_1v' in subset else None,
            'taxa_acerto_3v': round(subset['acerto_3v'].mean() * 100, 1) if 'acerto_3v' in subset else None,
            'taxa_acerto_5v': round(subset['acerto_5v'].mean() * 100, 1) if 'acerto_5v' in subset else None,
            'taxa_acerto_10v': round(subset['acerto_10v'].mean() * 100, 1) if 'acerto_10v' in subset else None,
        }
    
    return stats


def imprimir_estatisticas(stats):
    """Imprime as estatísticas de forma legível."""
    print(f"\n{'='*70}")
    print(f"📊 ESTATÍSTICAS DOS SINAIS DETECTADOS")
    print(f"{'='*70}")
    print(f"Total de sinais: {stats.get('total_sinais', 0)}")
    
    for tipo, dados in stats.get('por_tipo', {}).items():
        print(f"\n🎯 {tipo}:")
        print(f"   Quantidade: {dados['quantidade']}")
        print(f"   Retorno médio após 1 vela:  {dados.get('retorno_medio_1v')}%")
        print(f"   Retorno médio após 3 velas: {dados.get('retorno_medio_3v')}%")
        print(f"   Retorno médio após 5 velas: {dados.get('retorno_medio_5v')}%")
        print(f"   Retorno médio após 10 velas:{dados.get('retorno_medio_10v')}%")
        print(f"   Taxa de acerto em 1 vela:   {dados.get('taxa_acerto_1v')}%")
        print(f"   Taxa de acerto em 3 velas:  {dados.get('taxa_acerto_3v')}%")
        print(f"   Taxa de acerto em 5 velas:  {dados.get('taxa_acerto_5v')}%")
        print(f"   Taxa de acerto em 10 velas: {dados.get('taxa_acerto_10v')}%")
    
    print(f"{'='*70}\n")


# ============================================================
# SALVAMENTO
# ============================================================

def salvar_dados(df_completo, sinais, symbol, timeframe):
    """Salva os dados em CSV e JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Pasta de saída
    pasta = "dados_validacao"
    os.makedirs(pasta, exist_ok=True)
    
    # CSV completo (todas as velas, com indicadores)
    arquivo_completo = os.path.join(pasta, f"{symbol}_{timeframe}m_completo_{timestamp}.csv")
    df_completo.to_csv(arquivo_completo, index=False, encoding='utf-8')
    print(f"💾 Dados completos: {arquivo_completo} ({len(df_completo)} velas)")
    
    # CSV dos sinais (só onde houve sinal)
    if len(sinais) > 0:
        arquivo_sinais = os.path.join(pasta, f"{symbol}_{timeframe}m_sinais_{timestamp}.csv")
        sinais.to_csv(arquivo_sinais, index=False, encoding='utf-8')
        print(f"💾 Sinais detectados: {arquivo_sinais} ({len(sinais)} sinais)")
    else:
        arquivo_sinais = None
        print(f"⚠️ Nenhum sinal detectado para {symbol}")
    
    # JSON consolidado (mais fácil de parsear depois)
    dados_json = {
        'metadata': {
            'symbol': symbol,
            'timeframe': timeframe,
            'data_coleta': datetime.now().isoformat(),
            'total_velas': len(df_completo),
            'total_sinais': len(sinais),
            'rsi_period': int(df_completo['rsi_period'].iloc[0]) if 'rsi_period' in df_completo else None,
            'ma_period': int(df_completo['ma_period'].iloc[0]) if 'ma_period' in df_completo else None,
            'volume_lookback': int(df_completo['volume_lookback'].iloc[0]) if 'volume_lookback' in df_completo else None,
        },
        'sinais': sinais.to_dict(orient='records') if len(sinais) > 0 else [],
    }
    
    arquivo_json = os.path.join(pasta, f"{symbol}_{timeframe}m_validacao_{timestamp}.json")
    with open(arquivo_json, 'w', encoding='utf-8') as f:
        json.dump(dados_json, f, indent=2, ensure_ascii=False, default=str)
    print(f"💾 JSON de validação: {arquivo_json}")
    
    return arquivo_completo, arquivo_sinais, arquivo_json


# ============================================================
# ANÁLISE DE GRID (para você rodar na máquina antes de me enviar)
# ============================================================

def testar_varios_fatores(df, fatores=[1.2, 1.5, 2.0, 2.5, 3.0]):
    """
    Testa vários fatores de volume e retorna um resumo de performance.
    Útil para você já identificar boas configurações localmente.
    """
    resultados = []
    
    for fator in fatores:
        sinais = extrair_sinais_com_validacao(df, volume_fator=fator)
        if len(sinais) == 0:
            continue
        
        for tipo in ['COMPRA', 'VENDA']:
            sub = sinais[sinais['sinal'] == tipo]
            if len(sub) == 0:
                continue
            
            resultados.append({
                'volume_fator': fator,
                'tipo': tipo,
                'n_sinais': len(sub),
                'taxa_acerto_3v': round(sub['acerto_3v'].mean() * 100, 1) if 'acerto_3v' in sub else None,
                'taxa_acerto_5v': round(sub['acerto_5v'].mean() * 100, 1) if 'acerto_5v' in sub else None,
                'retorno_medio_3v': round(sub['retorno_3v'].mean(), 3) if 'retorno_3v' in sub else None,
                'retorno_medio_5v': round(sub['retorno_5v'].mean(), 3) if 'retorno_5v' in sub else None,
            })
    
    return pd.DataFrame(resultados)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Captura dados do MT5 para validação")
    parser.add_argument("--ativo", nargs="+", default=["VALE3"],
                        help="Ativo(s) a coletar. Padrão: VALE3")
    parser.add_argument("--timeframe", default="30",
                        help="Timeframe em minutos (1,2,5,15,30,60,240,D). Padrão: 30")
    parser.add_argument("--candles", type=int, default=2000,
                        help="Quantidade de candles. Padrão: 2000")
    parser.add_argument("--rsi", type=int, default=RSI_PERIOD_PADRAO,
                        help=f"Período do RSI. Padrão: {RSI_PERIOD_PADRAO}")
    parser.add_argument("--ma", type=int, default=MA_PERIOD_PADRAO,
                        help=f"Período da MA do RSI. Padrão: {MA_PERIOD_PADRAO}")
    parser.add_argument("--lookback", type=int, default=VOLUME_LOOKBACK_PADRAO,
                        help=f"Lookback do volume. Padrão: {VOLUME_LOOKBACK_PADRAO}")
    parser.add_argument("--fator", type=float, default=VOLUME_FATOR_PADRAO,
                        help=f"Fator de pico de volume. Padrão: {VOLUME_FATOR_PADRAO}")
    parser.add_argument("--grid", action="store_true",
                        help="Testar vários fatores de volume automaticamente")
    
    args = parser.parse_args()
    
    # Inicializa MT5
    if not mt5.initialize():
        print("❌ Erro ao inicializar MT5")
        return
    
    print(f"\n{'='*70}")
    print(f"📥 CAPTURADOR DE DADOS PARA VALIDAÇÃO")
    print(f"{'='*70}")
    print(f"Ativos: {args.ativo}")
    print(f"Timeframe: {args.timeframe}min")
    print(f"Candles: {args.candles}")
    print(f"RSI: {args.rsi} | MA RSI: {args.ma}")
    print(f"Volume lookback: {args.lookback} | Fator: {args.fator}")
    print(f"{'='*70}")
    
    estatisticas_globais = []
    resultados_grid = []
    
    for symbol in args.ativo:
        # Coleta
        df = coletar_dados_ativo(
            symbol,
            timeframe_str=args.timeframe,
            quantidade=args.candles,
            rsi_period=args.rsi,
            ma_period=args.ma,
            volume_lookback=args.lookback,
        )
        if df is None:
            continue
        
        # Detecta sinais com o fator especificado
        sinais = extrair_sinais_com_validacao(df, volume_fator=args.fator)
        
        # Estatísticas
        stats = gerar_estatisticas(sinais)
        stats['symbol'] = symbol
        estatisticas_globais.append(stats)
        imprimir_estatisticas(stats)
        
        # Salva
        salvar_dados(df, sinais, symbol, args.timeframe)
        
        # Grid search (opcional)
        if args.grid:
            print(f"\n🔬 Testando vários fatores de volume para {symbol}...")
            grid_result = testar_varios_fatores(df)
            if not grid_result.empty:
                grid_result['symbol'] = symbol
                resultados_grid.append(grid_result)
                print(grid_result.to_string(index=False))
    
    # Salva grid consolidado
    if resultados_grid:
        grid_final = pd.concat(resultados_grid, ignore_index=True)
        arquivo_grid = f"dados_validacao/grid_volume_fatores_{args.timeframe}m.csv"
        grid_final.to_csv(arquivo_grid, index=False)
        print(f"\n💾 Grid search salvo em: {arquivo_grid}")
    
    # Salva estatísticas consolidadas
    if estatisticas_globais:
        arquivo_stats = f"dados_validacao/estatisticas_{args.timeframe}m.json"
        with open(arquivo_stats, 'w', encoding='utf-8') as f:
            json.dump(estatisticas_globais, f, indent=2, ensure_ascii=False)
        print(f"💾 Estatísticas consolidadas: {arquivo_stats}")
    
    print(f"\n{'='*70}")
    print(f"✅ Coleta concluída! Dados em: ./dados_validacao/")
    print(f"{'='*70}")
    print(f"\n📌 Próximos passos:")
    print(f"   1. Me envie os arquivos CSV de sinais (ex: VALE3_30m_sinais_*.csv)")
    print(f"   2. Ou envie o JSON de validação completo")
    print(f"   3. Rode com --grid para já ver quais fatores funcionam melhor")
    print()
    
    mt5.shutdown()


if __name__ == "__main__":
    main()