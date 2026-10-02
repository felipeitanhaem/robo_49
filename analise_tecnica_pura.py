import MetaTrader5 as mt5

"""
SISTEMA DE ANÁLISE TÉCNICA PURA COM SYMBOLINFO
Versão: 3.0 - Análise Independente
Autor: Sistema de Análise Técnica Autônoma
Data: 2024

Este sistema toma decisões de trading baseadas APENAS nos dados do SymbolInfo.
Não depende de funções de intensidade sinal ou book de ofertas.

INSTALAÇÃO NECESSÁRIA:
pip install numpy pandas
"""

# ============================================================================
# IMPORTAÇÕES E CONFIGURAÇÕES
# ============================================================================

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CLASSE PRINCIPAL: ANALISADOR TÉCNICO PURA
# ============================================================================

class AnalisadorTecnicoPuro:
    """Sistema de análise técnica baseado apenas em SymbolInfo."""
    
    def __init__(self):
        self.historico = []
        self.parametros = self._definir_parametros()
        self.estatisticas = {}
        
    def _definir_parametros(self):
        """Define parâmetros técnicos para análise."""
        return {
            # Limites para spreads
            'spread_limites': {
                'excelente': 10,     # pontos
                'bom': 20,
                'regular': 40,
                'ruim': 100
            },
            
            # Limites para volumes
            'volume_limites': {
                'acao_br': {
                    'alto': 1000000,
                    'medio': 100000,
                    'baixo': 10000
                },
                'opcao': {
                    'alto': 10000,
                    'medio': 1000,
                    'baixo': 100
                }
            },
            
            # Tendência
            'tendencia_limites': {
                'forte_alta': 2.0,    # % de variação
                'moderada_alta': 0.5,
                'lateral': 0.2,
                'forte_baixa': -2.0
            },
            
            # Risco
            'risco_fatores': {
                'spread_alto': 30,    # pontos
                'volume_baixo': 1000,
                'volatilidade_alta': 5.0  # %
            }
        }
    
    def analisar_ativo(self, symbol_info, ativo=None, operacao="compra"):
        """
        Analisa um ativo usando apenas dados técnicos do SymbolInfo.
        
        Args:
            symbol_info: Dados do SymbolInfo (objeto ou dict)
            ativo: Nome do ativo (opcional)
            operacao: "compra" ou "venda"
        
        Returns:
            Dicionário com análise completa e recomendação
        """
        #print(f"\n{'='*70}")
        #print(f"📊 ANÁLISE TÉCNICA PURA: {ativo if ativo else 'Ativo'}")
        #print(f"🔄 Operação analisada: {operacao.upper()}")
        #print(f"{'='*70}")
        
        try:
            # Converter para dicionário se necessário
            dados = self._converter_para_dict(symbol_info)
            
            if not dados:
                raise ValueError("Dados do SymbolInfo inválidos")
            
            # 1. ANÁLISE DE PREÇO E TENDÊNCIA
            #print("\n💰 ANÁLISE DE PREÇO E TENDÊNCIA:")
            analise_preco = self._analisar_preco_tendencia(dados)
            #for chave, valor in analise_preco.items():
            #    if not chave.startswith('_'):
            #        print(f"   {chave}: {valor}")
            
            # 2. ANÁLISE DE LIQUIDEZ
            #print("\n📈 ANÁLISE DE LIQUIDEZ:")
            analise_liquidez = self._analisar_liquidez(dados, ativo)
            #for chave, valor in analise_liquidez.items():
            #    if not chave.startswith('_'):
            #        print(f"   {chave}: {valor}")
            
            # 3. ANÁLISE DE VOLUME
            #print("\n📊 ANÁLISE DE VOLUME:")
            analise_volume = self._analisar_volume(dados, ativo)
            #for chave, valor in analise_volume.items():
            #    if not chave.startswith('_'):
            #        print(f"   {chave}: {valor}")
            
            # 4. ANÁLISE DE RISCO
            #print("\n⚠️ ANÁLISE DE RISCO:")
            analise_risco = self._analisar_risco_tecnico(dados)
            #for chave, valor in analise_risco.items():
            #    if not chave.startswith('_'):
            #        print(f"   {chave}: {valor}")
            
            # 5. ANÁLISE DE TIMING
            #print("\n⏰ ANÁLISE DE TIMING:")
            analise_timing = self._analisar_timing(dados)
            #for chave, valor in analise_timing.items():
            #    if not chave.startswith('_'):
            #        print(f"   {chave}: {valor}")
            
            # 6. DECISÃO FINAL
            #print("\n🎯 DECISÃO TÉCNICA:")
            decisao = self._tomar_decisao_tecnica(
                analise_preco, 
                analise_liquidez, 
                analise_volume, 
                analise_risco, 
                analise_timing,
                operacao
            )
            
            #print(f"\n{'='*70}")
          #  print(f"✅ DECISÃO.: PARA {operacao} EM {ativo} {decisao['decisao']}")
            #print(f"📊 Confiança: {decisao['confianca']:.1%}")
            #print(f"🎯 Pontuação: {decisao['pontuacao']:.1f}/10")
          #  print(f"💡 Motivo: {decisao['motivo']}")
            #print(f"{'='*70}")
            
            # Registrar análise
            registro = {
                'timestamp': datetime.now(),
                'ativo': ativo,
                'operacao': operacao,
                'dados': dados,
                'analises': {
                    'preco': analise_preco,
                    'liquidez': analise_liquidez,
                    'volume': analise_volume,
                    'risco': analise_risco,
                    'timing': analise_timing
                },
                'decisao': decisao
            }
            
            self.historico.append(registro)
            
            return registro
            
        except Exception as e:
            print(f"⚠️ Erro na análise técnica: {e}")
            return {
                'erro': str(e),
                'decisao': {
                    'decisao': 'ERRO_ANALISE',
                    'confianca': 0.0,
                    'motivo': f'Erro na análise: {e}'
                }
            }
    
    def _converter_para_dict(self, symbol_info):
        """Converte SymbolInfo para dicionário."""
        if isinstance(symbol_info, dict):
            return symbol_info
        elif hasattr(symbol_info, '_asdict'):
            return symbol_info._asdict()
        else:
            # Extrair atributos do objeto
            dados = {}
            for attr in dir(symbol_info):
                if not attr.startswith('_'):
                    try:
                        dados[attr] = getattr(symbol_info, attr)
                    except:
                        pass
            return dados
    
    def _analisar_preco_tendencia(self, dados):
        """Analisa preço e tendência do ativo."""
        try:
            # Dados básicos
            bid = float(dados.get('bid', 0))
            ask = float(dados.get('ask', 0))
            last = float(dados.get('last', 0))
            bidhigh = float(dados.get('bidhigh', 0))
            bidlow = float(dados.get('bidlow', 0))
            session_open = float(dados.get('session_open', 0))
            price_change = float(dados.get('price_change', 0))
            
            # Preço de referência
            preco_atual = bid if bid > 0 else last
            
            # 1. Variação do dia
            if session_open > 0:
                variacao_dia = ((preco_atual - session_open) / session_open) * 100
            else:
                variacao_dia = 0
            
            # 2. Posição na faixa do dia
            if bidhigh > bidlow and bidlow > 0:
                posicao_faixa = ((bid - bidlow) / (bidhigh - bidlow)) * 100
            else:
                posicao_faixa = 50
            
            # 3. Força da tendência
            if abs(variacao_dia) > self.parametros['tendencia_limites']['forte_alta']:
                forca_tendencia = "MUITO FORTE"
                pontuacao_tendencia = 10 if variacao_dia > 0 else 0
            elif abs(variacao_dia) > self.parametros['tendencia_limites']['moderada_alta']:
                forca_tendencia = "FORTE"
                pontuacao_tendencia = 8 if variacao_dia > 0 else 2
            elif abs(variacao_dia) > self.parametros['tendencia_limites']['lateral']:
                forca_tendencia = "MODERADA"
                pontuacao_tendencia = 6 if variacao_dia > 0 else 4
            else:
                forca_tendencia = "LATERAL"
                pontuacao_tendencia = 5
            
            # 4. Direção
            if variacao_dia > 0.5:
                direcao = "ALTA"
                recomendacao_tendencia = "📈 Tendência de alta"
            elif variacao_dia < -0.5:
                direcao = "BAIXA"
                recomendacao_tendencia = "📉 Tendência de baixa"
            else:
                direcao = "NEUTRA"
                recomendacao_tendencia = "➡️ Mercado lateralizado"
            
            # 5. Momentum
            momentum = price_change if price_change != 0 else variacao_dia
            
            return {
                'Preço Atual (Bid)': f"{bid:.2f}",
                'Ask': f"{ask:.2f}",
                'Último': f"{last:.2f}",
                'Variação Dia': f"{variacao_dia:.2f}%",
                'Posição na Faixa': f"{posicao_faixa:.1f}%",
                'Direção': direcao,
                'Força Tendência': forca_tendencia,
                'Momentum': f"{momentum:.3f}",
                '_pontuacao_tendencia': pontuacao_tendencia,
                '_recomendacao_tendencia': recomendacao_tendencia,
                '_variacao_dia': variacao_dia,
                '_posicao_faixa': posicao_faixa
            }
            
        except Exception as e:
            print(f"⚠️ Erro análise preço: {e}")
            return {'Erro': f'Erro análise preço: {e}'}
    
    def _analisar_liquidez(self, dados, ativo):
        """Analisa liquidez do ativo."""
        try:
            spread = float(dados.get('spread', 0))
            bid = float(dados.get('bid', 1))
            ask = float(dados.get('ask', 1))
            
            # Calcular spread percentual
            if bid > 0:
                spread_percentual = ((ask - bid) / bid) * 100
            else:
                spread_percentual = 0
            
            # Avaliar spread
            if spread <= self.parametros['spread_limites']['excelente']:
                qualidade_spread = "EXCELENTE"
                pontuacao_spread = 10
                recomendacao_spread = "✅ Spread ótimo para trading"
            elif spread <= self.parametros['spread_limites']['bom']:
                qualidade_spread = "BOM"
                pontuacao_spread = 7
                recomendacao_spread = "⚠️ Spread bom, operação viável"
            elif spread <= self.parametros['spread_limites']['regular']:
                qualidade_spread = "REGULAR"
                pontuacao_spread = 5
                recomendacao_spread = "⚠️ Spread regular, atenção ao custo"
            else:
                qualidade_spread = "RUIM"
                pontuacao_spread = 2
                recomendacao_spread = "⛔ Spread muito alto, evite operar"
            
            # Spread flutuante
            spread_float = dados.get('spread_float', False)
            
            return {
                'Spread (pontos)': f"{spread}",
                'Spread (%)': f"{spread_percentual:.4f}%",
                'Qualidade Spread': qualidade_spread,
                'Spread Flutuante': "SIM" if spread_float else "NÃO",
                'Pontuação Spread': f"{pontuacao_spread}/10",
                '_pontuacao_spread': pontuacao_spread,
                '_recomendacao_spread': recomendacao_spread
            }
            
        except Exception as e:
            print(f"⚠️ Erro análise liquidez: {e}")
            return {'Erro': f'Erro análise liquidez: {e}'}
    
    def _analisar_volume(self, dados, ativo):
        """Analisa volume do ativo."""
        try:
            volume = float(dados.get('volume', 0))
            volume_real = float(dados.get('volume_real', 0))
            session_volume = float(dados.get('session_volume', 0))
            
            # Usar maior volume disponível
            volume_efetivo = max(volume, volume_real, session_volume)
            
            # Identificar tipo de ativo
            if ativo and ('H' in ativo.upper() or len(ativo) > 5):
                tipo = 'opcao'
                limites = self.parametros['volume_limites']['opcao']
            else:
                tipo = 'acao_br'
                limites = self.parametros['volume_limites']['acao_br']
            
            # Avaliar volume
            if volume_efetivo >= limites['alto']:
                qualidade_volume = "ALTO"
                pontuacao_volume = 10
                recomendacao_volume = "✅ Volume excelente, boa liquidez"
            elif volume_efetivo >= limites['medio']:
                qualidade_volume = "MODERADO"
                pontuacao_volume = 7
                recomendacao_volume = "⚠️ Volume moderado, operação viável"
            elif volume_efetivo >= limites['baixo']:
                qualidade_volume = "BAIXO"
                pontuacao_volume = 4
                recomendacao_volume = "⚠️ Volume baixo, risco de execução"
            else:
                qualidade_volume = "MUITO BAIXO"
                pontuacao_volume = 1
                recomendacao_volume = "⛔ Volume muito baixo, evite operar"
            
            # Volume vs média
            volume_min = float(dados.get('volume_min', 100))
            if volume_min > 0:
                relacao_volume = volume_efetivo / volume_min
            else:
                relacao_volume = 1
            
            return {
                'Volume Atual': f"{volume_efetivo:,.0f}",
                'Volume Mínimo': f"{volume_min:,.0f}",
                'Relação Volume': f"{relacao_volume:.1f}x",
                'Qualidade Volume': qualidade_volume,
                'Tipo Ativo': tipo.upper(),
                'Pontuação Volume': f"{pontuacao_volume}/10",
                '_pontuacao_volume': pontuacao_volume,
                '_recomendacao_volume': recomendacao_volume,
                '_volume_efetivo': volume_efetivo
            }
            
        except Exception as e:
            print(f"⚠️ Erro análise volume: {e}")
            return {'Erro': f'Erro análise volume: {e}'}
    
    def _analisar_risco_tecnico(self, dados):
        """Analisa riscos técnicos do ativo."""
        try:
            fatores_risco = []
            pontuacao_risco = 10  # Começa com 10, subtrai por riscos
            
            # 1. Spread alto
            spread = float(dados.get('spread', 0))
            if spread > self.parametros['risco_fatores']['spread_alto']:
                fatores_risco.append(f"Spread muito alto ({spread} pontos)")
                pontuacao_risco -= 3
            
            # 2. Volume baixo
            volume = float(dados.get('volume', 0))
            if volume < self.parametros['risco_fatores']['volume_baixo']:
                fatores_risco.append(f"Volume muito baixo ({volume:,.0f})")
                pontuacao_risco -= 3
            
            # 3. Volatilidade alta
            price_volatility = float(dados.get('price_volatility', 0))
            if price_volatility > self.parametros['risco_fatores']['volatilidade_alta']:
                fatores_risco.append(f"Alta volatilidade ({price_volatility:.1f}%)")
                pontuacao_risco -= 2
            
            # 4. Horário (se disponível)
            time = dados.get('time', 0)
            if time > 0:
                hora = datetime.fromtimestamp(time).hour
                if hora < 10 or hora > 17:  # Fora do horário comercial
                    fatores_risco.append(f"Fora do horário ideal (Hora: {hora}h)")
                    pontuacao_risco -= 1
            
            # 5. Gap de abertura
            session_open = float(dados.get('session_open', 0))
            last = float(dados.get('last', 0))
            if session_open > 0 and last > 0:
                gap_percentual = abs((last - session_open) / session_open * 100)
                if gap_percentual > 3:
                    fatores_risco.append(f"Gap de abertura ({gap_percentual:.1f}%)")
                    pontuacao_risco -= 2
            
            # Classificação do risco
            if pontuacao_risco >= 8:
                classificacao = "BAIXO"
                recomendacao = "✅ Risco controlado"
            elif pontuacao_risco >= 6:
                classificacao = "MODERADO"
                recomendacao = "⚠️ Risco moderado, operar com cautela"
            elif pontuacao_risco >= 4:
                classificacao = "ALTO"
                recomendacao = "⚠️ Risco alto, reduzir tamanho da operação"
            else:
                classificacao = "MUITO ALTO"
                recomendacao = "⛔ Risco muito alto, evitar operação"
            
            # Garantir pontuação entre 0-10
            pontuacao_risco = max(0, min(10, pontuacao_risco))
            
            return {
                'Fatores de Risco': ", ".join(fatores_risco) if fatores_risco else "Nenhum identificado",
                'Classificação Risco': classificacao,
                'Pontuação Risco': f"{pontuacao_risco:.1f}/10",
                '_pontuacao_risco': pontuacao_risco,
                '_recomendacao_risco': recomendacao,
                '_num_fatores_risco': len(fatores_risco)
            }
            
        except Exception as e:
            print(f"⚠️ Erro análise risco: {e}")
            return {'Erro': f'Erro análise risco: {e}'}
    
    def _analisar_timing(self, dados):
        """Analisa timing da operação."""
        try:
            fatores_timing = []
            pontuacao_timing = 5  # Neutro inicialmente
            
            # 1. Horário do dia
            time = dados.get('time', 0)
            if time > 0:
                hora = datetime.fromtimestamp(time).hour
                if 10 <= hora <= 16:
                    fatores_timing.append("Horário de maior liquidez")
                    pontuacao_timing += 2
                elif hora < 9 or hora > 17:
                    fatores_timing.append("Fora do horário comercial")
                    pontuacao_timing -= 1
            
            # 2. Posição no dia (baseado no volume acumulado)
            session_volume = float(dados.get('session_volume', 0))
            volume = float(dados.get('volume', 0))
            
            if session_volume > 0 and volume > 0:
                percentual_dia = (volume / session_volume) * 100
                if percentual_dia > 80:
                    fatores_timing.append("Final do dia - volume consolidado")
                elif percentual_dia < 20:
                    fatores_timing.append("Início do dia - volume em formação")
            
            # 3. Dia da semana (se possível inferir da data)
            if time > 0:
                dia_semana = datetime.fromtimestamp(time).weekday()
                # 0 = segunda, 4 = sexta
                if dia_semana == 4:  # Sexta-feira
                    fatores_timing.append("Sexta-feira - cuidado com weekend gap")
                    pontuacao_timing -= 1
                elif dia_semana == 0:  # Segunda-feira
                    fatores_timing.append("Segunda-feira - abertura da semana")
                    pontuacao_timing += 1
            
            # Avaliação final
            if pontuacao_timing >= 7:
                recomendacao = "✅ Timing favorável"
            elif pontuacao_timing >= 5:
                recomendacao = "⚠️ Timing neutro"
            else:
                recomendacao = "⛔ Timing desfavorável"
            
            pontuacao_timing = max(0, min(10, pontuacao_timing))
            
            return {
                'Fatores Timing': ", ".join(fatores_timing) if fatores_timing else "Sem fatores específicos",
                'Pontuação Timing': f"{pontuacao_timing:.1f}/10",
                '_pontuacao_timing': pontuacao_timing,
                '_recomendacao_timing': recomendacao
            }
            
        except Exception as e:
            print(f"⚠️ Erro análise timing: {e}")
            return {'Erro': f'Erro análise timing: {e}'}
    
    def _tomar_decisao_tecnica(self, preco, liquidez, volume, risco, timing, operacao):
        """Toma decisão baseada apenas em análise técnica."""
        try:
            # Extrair pontuações
            p_tendencia = preco.get('_pontuacao_tendencia', 5)
            p_spread = liquidez.get('_pontuacao_spread', 5)
            p_volume = volume.get('_pontuacao_volume', 5)
            p_risco = risco.get('_pontuacao_risco', 5)
            p_timing = timing.get('_pontuacao_timing', 5)
            
            # Fatores específicos
            variacao_dia = preco.get('_variacao_dia', 0)
            direcao = preco.get('Direção', 'NEUTRA')
            num_fatores_risco = risco.get('_num_fatores_risco', 0)
            
            # 1. Pontuação base
            pontuacao_base = (
                p_tendencia * 0.25 +      # Tendência é importante
                p_spread * 0.25 +         # Spread crucial para custo
                p_volume * 0.20 +         # Volume para liquidez
                p_risco * 0.20 +          # Risco deve ser considerado
                p_timing * 0.10           # Timing tem menor peso
            )
            
            # 2. Ajustes baseados na operação
            if operacao.lower() == "compra":
                # Para compra: queremos tendência de alta ou fundo
                if direcao == "ALTA":
                    pontuacao_base *= 1.1  # Bônus
                elif direcao == "BAIXA":
                    pontuacao_base *= 0.9  # Penalidade
                
                # Posição na faixa - comprar perto do fundo é bom
                posicao_faixa = preco.get('_posicao_faixa', 50)
                if posicao_faixa < 30:
                    pontuacao_base *= 1.05  # Bom para compra (perto do fundo)
                
            elif operacao.lower() == "venda":
                # Para venda: queremos tendência de baixa ou topo
                if direcao == "BAIXA":
                    pontuacao_base *= 1.1  # Bônus
                elif direcao == "ALTA":
                    pontuacao_base *= 0.9  # Penalidade
                
                # Posição na faixa - vender perto do topo é bom
                posicao_faixa = preco.get('_posicao_faixa', 50)
                if posicao_faixa > 70:
                    pontuacao_base *= 1.05  # Bom para venda (perto do topo)
            
            # 3. Penalidades por fatores críticos
            if num_fatores_risco >= 3:
                pontuacao_base *= 0.7  # Penalidade forte
            elif num_fatores_risco >= 2:
                pontuacao_base *= 0.8
            elif num_fatores_risco >= 1:
                pontuacao_base *= 0.9
            
            # Spread muito ruim
            if p_spread < 3:
                pontuacao_base *= 0.7
            
            # Volume muito baixo
            if p_volume < 3:
                pontuacao_base *= 0.8
            
            # 4. Garantir limites
            pontuacao_final = max(0, min(10, pontuacao_base))
            
            # 5. Gerar decisão
            if pontuacao_final >= 7.5:
                if p_spread >= 7 and p_volume >= 7:
                    decisao = "EXECUTAR"
                    confianca = min(0.95, pontuacao_final / 10)
                    motivo = "Condições técnicas excelentes"
                else:
                    decisao = "EXECUTAR_COM_CUIDADO"
                    confianca = pontuacao_final / 10 * 0.8
                    motivo = "Condições boas com algumas ressalvas"
            
            elif pontuacao_final >= 6.0:
                decisao = "AGUARDAR_MELHOR_OPORTUNIDADE"
                confianca = 0.5
                motivo = "Condições medianas, aguardar melhora"
            
            elif pontuacao_final >= 4.0:
                decisao = "EVITAR"
                confianca = 0.3
                motivo = "Condições desfavoráveis"
            
            else:
                decisao = "BLOQUEAR"
                confianca = 0.1
                motivo = "Condições muito ruins - Alto risco"
            
            # 6. Adicionar detalhes ao motivo
            detalhes = []
            
            if direcao != "NEUTRA":
                detalhes.append(f"Tendência: {direcao}")
            
            if abs(variacao_dia) > 2:
                sinal = "+" if variacao_dia > 0 else ""
                detalhes.append(f"Variação: {sinal}{variacao_dia:.1f}%")
            
            if num_fatores_risco > 0:
                detalhes.append(f"Riscos: {num_fatores_risco}")
            
            if detalhes:
                motivo += " | " + " | ".join(detalhes)
            
            return {
                'decisao': decisao,
                'confianca': confianca,
                'pontuacao': pontuacao_final,
                'motivo': motivo,
                'detalhes_pontuacao': {
                    'tendencia': p_tendencia,
                    'spread': p_spread,
                    'volume': p_volume,
                    'risco': p_risco,
                    'timing': p_timing
                }
            }
            
        except Exception as e:
            print(f"⚠️ Erro na decisão técnica: {e}")
            return {
                'decisao': 'ERRO_DECISAO',
                'confianca': 0.0,
                'pontuacao': 0,
                'motivo': f'Erro na decisão: {e}'
            }
    
    def analisar_lista_ativos(self, lista_ativos_symbolinfo, operacao="compra"):
        """
        Analisa múltiplos ativos e retorna ranking.
        
        Args:
            lista_ativos_symbolinfo: Lista de tuplas [(ativo1, symbol_info1), ...]
            operacao: Tipo de operação ("compra" ou "venda")
        
        Returns:
            DataFrame com ranking de ativos
        """
        print(f"\n{'#'*70}")
        print(f"📋 ANÁLISE EM LOTE: {len(lista_ativos_symbolinfo)} ativos")
        print(f"{'#'*70}")
        
        resultados = []
        
        for ativo, symbol_info in lista_ativos_symbolinfo:
            try:
                print(f"\nAnalisando {ativo}...")
                
                analise = self.analisar_ativo(symbol_info, ativo, operacao)
                
                if 'decisao' in analise and 'pontuacao' in analise['decisao']:
                    resultados.append({
                        'ativo': ativo,
                        'decisao': analise['decisao']['decisao'],
                        'confianca': analise['decisao']['confianca'],
                        'pontuacao': analise['decisao']['pontuacao'],
                        'tendencia': analise['analises']['preco'].get('Direção', ''),
                        'variacao_dia': analise['analises']['preco'].get('Variação Dia', '0%'),
                        'spread': analise['analises']['liquidez'].get('Spread (pontos)', '0'),
                        'volume': analise['analises']['volume'].get('Volume Atual', '0')
                    })
                
            except Exception as e:
                print(f"⚠️ Erro ao analisar {ativo}: {e}")
                continue
        
        # Criar ranking
        if resultados:
            df = pd.DataFrame(resultados)
            df = df.sort_values(['pontuacao', 'confianca'], ascending=[False, False])
            
            print(f"\n{'='*70}")
            print(f"🏆 RANKING DE ATIVOS - {operacao.upper()}")
            print(f"{'='*70}")
            
            for i, (_, row) in enumerate(df.iterrows(), 1):
                if i <= 15:  # Mostrar top 15
                    print(f"{i:2d}. {row['ativo']:10} | {row['decisao']:25} | "
                          f"Pts: {row['pontuacao']:.1f} | Conf: {row['confianca']:.1%} | "
                          f"Ten: {row['tendencia']:6} | Var: {row['variacao_dia']}")
            
            return df
        
        return pd.DataFrame()


##------------
#=========================================
#
#=========================================

class AnalisadorBookOfertas:
    """Analisa o book de ofertas considerando a operação (compra/venda)."""
    
    def __init__(self):
        self.limites_analise = {
            'niveis_considerar': 10,
            'volume_minimo_nivel': 5.0,
            'desbalanceamento_significativo': 1.5
        }
    
    def analisar_book(self, book_info, preco_atual_ask, operacao="compra"):
        """
        Analisa book considerando a operação.
        
        Args:
            book_info: Dados do book
            preco_atual_ask: Preço Ask atual
            operacao: "compra" ou "venda"
        """
        if not book_info:
            return {'erro': 'Book de ofertas vazio ou indisponível'}
        
        # Separar ofertas de compra (BID) e venda (ASK)
        ofertas_compra = []  # type=2 (BID)
        ofertas_venda = []   # type=1 (ASK)

        for entrada in book_info:
            if entrada.type == 2:  # BID
                ofertas_compra.append({
                    'preco': entrada.price,
                    'volume': entrada.volume
                })
            elif entrada.type == 1:  # ASK
                ofertas_venda.append({
                    'preco': entrada.price,
                    'volume': entrada.volume
                })

        # Ordenar
        ofertas_compra.sort(key=lambda x: x['preco'], reverse=True)
        ofertas_venda.sort(key=lambda x: x['preco'])

        # Analisar os N primeiros níveis
        niveis_analisar = self.limites_analise['niveis_considerar']
        compra_top = ofertas_compra[:niveis_analisar]
        venda_top = ofertas_venda[:niveis_analisar]

        # 1. Pressão Imediata
        if compra_top and venda_top:
            volume_melhor_compra = compra_top[0]['volume']
            volume_melhor_venda = venda_top[0]['volume']
            razao_venda_compra = volume_melhor_venda / volume_melhor_compra if volume_melhor_compra > 0 else 999
        else:
            volume_melhor_compra = volume_melhor_venda = razao_venda_compra = 0

        # 2. Profundidade do Mercado
        profundidade_compra = sum(n['volume'] for n in compra_top)
        profundidade_venda = sum(n['volume'] for n in venda_top)
        desbalanceamento_total = profundidade_venda / profundidade_compra if profundidade_compra > 0 else 999

        # 3. Parede de Ordens
        parede_compra = self._identificar_parede(compra_top, preco_atual_ask, lado='compra')
        parede_venda = self._identificar_parede(venda_top, preco_atual_ask, lado='venda')

        # 4. Spread Efetivo
        spread_efetivo = 0
        if venda_top and compra_top:
            spread_efetivo = venda_top[0]['preco'] - compra_top[0]['preco']

        # 5. Calcular pontuação CONSIDERANDO A OPERAÇÃO
        classificacao = self._classificar_liquidez_book(
            spread_efetivo, desbalanceamento_total, profundidade_compra, profundidade_venda, operacao
        )
        #print("chegou aqui no book")    
        return {
            'resumo': {
                'melhor_compra': compra_top[0]['preco'] if compra_top else 0,
                'melhor_venda': venda_top[0]['preco'] if venda_top else 0,
                'volume_melhor_compra': volume_melhor_compra,
                'volume_melhor_venda': volume_melhor_venda,
                'spread_efetivo_points': spread_efetivo,
                'spread_efetivo_percent': (spread_efetivo / preco_atual_ask * 100) if preco_atual_ask > 0 else 0,
                'profundidade_compra': profundidade_compra,
                'profundidade_venda': profundidade_venda,
                'desbalanceamento_venda_compra': desbalanceamento_total,
                'operacao_analisada': operacao
            },
            'paredes_ordem': {
                'parede_compra': parede_compra,
                'parede_venda': parede_venda,
            },
            'classificacao_book': classificacao,
            'detalhes_niveis': {
                'top_compras': compra_top,
                'top_vendas': venda_top
                
            }
        }
    
    def _classificar_liquidez_book(self, spread, desbalanceamento, profundidade_compra, profundidade_venda, operacao):
        """Classifica considerando a operação (compra/venda)."""
        
        # Critério 1: Spread (igual para ambos)
        if spread <= 0.01:
            pontuacao_spread = 10
        elif spread <= 0.05:
            pontuacao_spread = 7
        elif spread <= 0.10:
            pontuacao_spread = 5
        else:
            pontuacao_spread = 2
        
        # Critério 2: Desbalanceamento - DIFERENTE para compra vs venda
        if operacao.lower() == "compra":
            # Para COMPRA: queremos mais volume de venda (maior liquidez para comprar)
            # Desbalanceamento ideal para compra: > 1.0 (mais venda que compra)
            if desbalanceamento >= 1.5:
                pontuacao_balance = 10  # Excelente para comprar
            elif desbalanceamento >= 1.2:
                pontuacao_balance = 8
            elif desbalanceamento >= 1.0:
                pontuacao_balance = 7
            elif desbalanceamento >= 0.8:
                pontuacao_balance = 5
            elif desbalanceamento >= 0.5:
                pontuacao_balance = 3
            else:
                pontuacao_balance = 1  # Muito ruim para comprar
                
        else:  # operacao == "venda"
            # Para VENDA: queremos mais volume de compra (maior liquidez para vender)
            # Desbalanceamento ideal para venda: < 1.0 (mais compra que venda)
            if desbalanceamento <= 0.5:
                pontuacao_balance = 10  # Excelente para vender
            elif desbalanceamento <= 0.8:
                pontuacao_balance = 8
            elif desbalanceamento <= 1.0:
                pontuacao_balance = 7
            elif desbalanceamento <= 1.2:
                pontuacao_balance = 5
            elif desbalanceamento <= 1.5:
                pontuacao_balance = 3
            else:
                pontuacao_balance = 1  # Muito ruim para vender
        
        # Critério 3: Profundidade absoluta
        volume_minimo = 50.0
        if profundidade_compra > volume_minimo and profundidade_venda > volume_minimo:
            pontuacao_profundidade = 10
        elif profundidade_compra > volume_minimo or profundidade_venda > volume_minimo:
            pontuacao_profundidade = 6
        else:
            pontuacao_profundidade = 3
        
        # Pontuação final (ponderada)
        pontuacao_final = (pontuacao_spread * 0.3 +
                          pontuacao_balance * 0.4 +  # Maior peso para o balanceamento
                          pontuacao_profundidade * 0.3)
        
        # Classificação textual
        if pontuacao_final >= 8:
            classificacao = f"EXCELENTE PARA {operacao.upper()}"
            recomendacao = f"✅ Book muito favorável para {operacao}"
        elif pontuacao_final >= 6:
            classificacao = f"BOM PARA {operacao.upper()}"
            recomendacao = f"⚠️ Book adequado para {operacao}"
        elif pontuacao_final >= 4:
            classificacao = f"REGULAR PARA {operacao.upper()}"
            recomendacao = f"⚠️ Book com ressalvas para {operacao}"
        else:
            classificacao = f"RUIM PARA {operacao.upper()}"
            recomendacao = f"⛔ Book desfavorável para {operacao}"
        
        return {
            'classificacao': classificacao,
            'recomendacao': recomendacao,
            'pontuacao_total': pontuacao_final,
            'detalhes_pontuacao': {
                'spread': pontuacao_spread,
                'balanceamento': pontuacao_balance,
                'profundidade': pontuacao_profundidade
            },
            'desbalanceamento_atual': desbalanceamento
        }
    
    def _identificar_parede(self, ofertas, preco_atual, lado='compra'):
        """Identifica paredes de volume."""
        if not ofertas:
            return None

        limite_volume_parede = 100.0

        for oferta in ofertas:
            if oferta['volume'] >= limite_volume_parede:
                distancia_percentual = abs(oferta['preco'] - preco_atual) / preco_atual * 100
                return {
                    'preco': oferta['preco'],
                    'volume': oferta['volume'],
                    'distancia_percentual': distancia_percentual,
                    'lado': lado
                }
        return None

#....................................
"""class AnalisadorBookOfertas:
    #Analisa o book de ofertas (Depth of Market) para gerar insights de execução e pressão.

    def __init__(self):
        self.limites_analise = {
            'niveis_considerar': 10,  # Quantos níveis de preço analisar no book
            'volume_minimo_nivel': 5.0,  # Volume mínimo para considerar um nível relevante
            'desbalanceamento_significativo': 1.5  # Razão V/B > 1.5 indica pressão
        }

    def analisar_book(self, book_info, preco_atual_ask):
        
        #Processa o book de ofertas retornado por mt5.market_book_get().

        #Args:
        #    book_info: Tuple de objetos BookInfo (retornada por market_book_get).
        #    preco_atual_ask: Preço Ask atual (para referência).

        #Returns:
        #    Dict com análise consolidada.
        
        if not book_info:
            return {'erro': 'Book de ofertas vazio ou indisponível'}

        # Separar ofertas de compra (BID) e venda (ASK)
        ofertas_compra = []  # type=2 (BID)
        ofertas_venda = []   # type=1 (ASK)

        for entrada in book_info:
            if entrada.type == 2:  # BID
                ofertas_compra.append({
                    'preco': entrada.price,
                    'volume': entrada.volume
                })
            elif entrada.type == 1:  # ASK
                ofertas_venda.append({
                    'preco': entrada.price,
                    'volume': entrada.volume
                })

        # Ordenar: compras por preço mais alto, vendas por preço mais baixo
        ofertas_compra.sort(key=lambda x: x['preco'], reverse=True)
        ofertas_venda.sort(key=lambda x: x['preco'])

        # Analisar os N primeiros níveis
        niveis_analisar = self.limites_analise['niveis_considerar']
        compra_top = ofertas_compra[:niveis_analisar]
        venda_top = ofertas_venda[:niveis_analisar]

        # 1. Pressão Imediata (Volume nos melhores preços)
        if compra_top and venda_top:
            volume_melhor_compra = compra_top[0]['volume']
            volume_melhor_venda = venda_top[0]['volume']
            razao_venda_compra = volume_melhor_venda / volume_melhor_compra if volume_melhor_compra > 0 else 999
        else:
            volume_melhor_compra = volume_melhor_venda = razao_venda_compra = 0

        # 2. Profundidade do Mercado (Soma do volume nos N níveis)
        profundidade_compra = sum(n['volume'] for n in compra_top)
        profundidade_venda = sum(n['volume'] for n in venda_top)
        desbalanceamento_total = profundidade_venda / profundidade_compra if profundidade_compra > 0 else 999

        # 3. Parede de Ordens (Identificar grandes volumes)
        parede_compra = self._identificar_parede(compra_top, preco_atual_ask, lado='compra')
        parede_venda = self._identificar_parede(venda_top, preco_atual_ask, lado='venda')

        # 4. Spread Efetivo no Book (Diferença entre melhor venda e melhor compra)
        spread_efetivo = 0
        if venda_top and compra_top:
            spread_efetivo = venda_top[0]['preco'] - compra_top[0]['preco']

        # 5. Calcular pontuação/classificação
        classificacao = self._classificar_liquidez_book(
            spread_efetivo, desbalanceamento_total, profundidade_compra, profundidade_venda
        )

        return {
            'resumo': {
                'melhor_compra': compra_top[0]['preco'] if compra_top else 0,
                'melhor_venda': venda_top[0]['preco'] if venda_top else 0,
                'volume_melhor_compra': volume_melhor_compra,
                'volume_melhor_venda': volume_melhor_venda,
                'spread_efetivo_points': spread_efetivo,
                'spread_efetivo_percent': (spread_efetivo / preco_atual_ask * 100) if preco_atual_ask > 0 else 0,
                'profundidade_compra': profundidade_compra,
                'profundidade_venda': profundidade_venda,
                'desbalanceamento_venda_compra': desbalanceamento_total,
            },
            'paredes_ordem': {
                'parede_compra': parede_compra,
                'parede_venda': parede_venda,
            },
            'classificacao_book': classificacao,
            'detalhes_niveis': {
                'top_compras': compra_top,
                'top_vendas': venda_top
            }
        }

    def _identificar_parede(self, ofertas, preco_atual, lado='compra'):
        #Identifica 'paredes' de volume (ordens grandes) no book.
        if not ofertas:
            return None

        limite_volume_parede = 100.0  # Volume mínimo para ser considerado "parede"

        for oferta in ofertas:
            if oferta['volume'] >= limite_volume_parede:
                distancia_percentual = abs(oferta['preco'] - preco_atual) / preco_atual * 100
                return {
                    'preco': oferta['preco'],
                    'volume': oferta['volume'],
                    'distancia_percentual': distancia_percentual,
                    'lado': lado
                }
        return None

    def _classificar_liquidez_book(self, spread, desbalanceamento, profundidade_compra, profundidade_venda):
        Classifica a qualidade da liquidez baseada no book.
        # Critério 1: Spread
        if spread <= 0.01:  # Ex: 1 pip ou menos
            pontuacao_spread = 10
        elif spread <= 0.05:
            pontuacao_spread = 7
        elif spread <= 0.10:
            pontuacao_spread = 5
        else:
            pontuacao_spread = 2

        # Critério 2: Desbalanceamento (próximo de 1 é ideal)
        if 0.8 <= desbalanceamento <= 1.2:
            pontuacao_balance = 10
        elif 0.5 <= desbalanceamento <= 1.5:
            pontuacao_balance = 7
        elif 0.2 <= desbalanceamento <= 2.0:
            pontuacao_balance = 5
        else:
            pontuacao_balance = 2

        # Critério 3: Profundidade absoluta
        volume_minimo = 50.0
        if profundidade_compra > volume_minimo and profundidade_venda > volume_minimo:
            pontuacao_profundidade = 10
        elif profundidade_compra > volume_minimo or profundidade_venda > volume_minimo:
            pontuacao_profundidade = 6
        else:
            pontuacao_profundidade = 3

        # Pontuação final (ponderada)
        pontuacao_final = (pontuacao_spread * 0.4 +
                          pontuacao_balance * 0.3 +
                          pontuacao_profundidade * 0.3)

        # Classificação textual
        if pontuacao_final >= 8:
            classificacao = "EXCELENTE"
            recomendacao = "✅ Book muito líquido e balanceado"
        elif pontuacao_final >= 6:
            classificacao = "BOM"
            recomendacao = "⚠️ Book adequado para operação"
        elif pontuacao_final >= 4:
            classificacao = "REGULAR"
            recomendacao = "⚠️ Book com alguma assimetria, cautela"
        else:
            classificacao = "RUIM"
            recomendacao = "⛔ Book ilíquido ou muito desbalanceado"

        return {
            'classificacao': classificacao,
            'recomendacao': recomendacao,
            'pontuacao_total': pontuacao_final,
            'detalhes_pontuacao': {
                'spread': pontuacao_spread,
                'balanceamento': pontuacao_balance,
                'profundidade': pontuacao_profundidade
            }
        }


"""



# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

def criar_simbolo_exemplo():
    """Cria exemplo de SymbolInfo para testes."""
    class SimboloExemplo:
        def __init__(self):
            # Dados do exemplo fornecido
            self.bid = 69.74
            self.ask = 69.87
            self.last = 69.87
            self.bidhigh = 70.41
            self.bidlow = 68.9
            self.session_open = 69.78
            self.price_change = 0.129
            self.spread = 13
            self.spread_float = True
            self.volume = 26800
            self.volume_real = 26800.0
            self.session_volume = 23081300.0
            self.volume_min = 100.0
            self.price_volatility = 0.0
            self.time = 1765309500
            self.description = 'VALE        ON      NM'
    
    return SimboloExemplo()

def analisar_ativo_rapido(symbol_info, ativo=None, operacao="compra"):
    """
    Função rápida para análise de um único ativo.
    
    Args:
        symbol_info: Dados do SymbolInfo
        ativo: Nome do ativo (opcional)
        operacao: "compra" ou "venda"
    
    Returns:
        Decisão técnica
    """
    analisador = AnalisadorTecnicoPuro()
    resultado = analisador.analisar_ativo(symbol_info, ativo, operacao)
    return resultado.get('decisao', {})

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def exemplo_uso_completo():
    """Exemplo completo de uso do sistema."""
    print("\n" + "="*70)
    print("📚 EXEMPLO: ANÁLISE TÉCNICA PURA COM SYMBOLINFO")
    print("="*70)
    
    # 1. Criar analisador
    analisador = AnalisadorTecnicoPuro()
    
    # 2. Criar dados de exemplo
    symbol_info = criar_simbolo_exemplo()
    
    # 3. Analisar ativo
    print("\nExecutando análise para VALE3 - COMPRA...")
    resultado = analisador.analisar_ativo(
        symbol_info=symbol_info,
        ativo="VALE3",
        operacao="compra"
    )
    
    # 4. Mostrar resumo
    if 'decisao' in resultado:
        print(f"\n📋 RESUMO DA ANÁLISE:")
        print(f"  Ativo: {resultado.get('ativo', 'Desconhecido')}")
        print(f"  Operação: {resultado.get('operacao', 'Desconhecida')}")
        print(f"  Decisão: {resultado['decisao']['decisao']}")
        print(f"  Pontuação: {resultado['decisao']['pontuacao']:.1f}/10")
        print(f"  Confiança: {resultado['decisao']['confianca']:.1%}")
    
    return analisador

# ============================================================================
# INTEGRAÇÃO COM MT5
# ============================================================================

def usar_com_mt5():
    """
    Exemplo de como usar com MetaTrader 5.
    
    Este exemplo mostra como integrar o analisador com dados reais do MT5.
    """
    
    print("\n📌 EXEMPLO DE INTEGRAÇÃO COM META TRADER 5:")
    print("""
# 1. Importar bibliotecas
import MetaTrader5 as mt5
from analise_tecnica_pura import AnalisadorTecnicoPuro

# 2. Inicializar MT5
mt5.initialize()

# 3. Criar analisador
analisador = AnalisadorTecnicoPuro()

# 4. Obter dados do ativo
ativo = "PETR4"
symbol_info = mt5.symbol_info(ativo)

if symbol_info is None:
    print(f"Ativo {ativo} não encontrado")
else:
    # 5. Analisar ativo
    resultado = analisador.analisar_ativo(
        symbol_info=symbol_info,
        ativo=ativo,
        operacao="compra"  # ou "venda"
    )
    
    # 6. Tomar decisão
    decisao = resultado['decisao']['decisao']
    confianca = resultado['decisao']['confianca']
    
    if decisao in ["EXECUTAR", "EXECUTAR_COM_CUIDADO"]:
        print(f"✅ OPERAR {ativo} | Confiança: {confianca:.1%}")
        # Colocar ordem aqui
    else:
        print(f"⛔ NÃO OPERAR {ativo} | Motivo: {resultado['decisao']['motivo']}")
    """)

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 SISTEMA DE ANÁLISE TÉCNICA PURA")
    print("="*70)
    print("Versão: 3.0 - Independente")
    print("Base: Apenas SymbolInfo da MT5")
    print("="*70)
    
    # Executar exemplo
    resposta = input("\nDeseja executar o exemplo? (s/n): ").strip().lower()
    
    if resposta == 's':
        sistema = exemplo_uso_completo()
        print(f"\n✅ Sistema pronto! Total de análises: {len(sistema.historico)}")
    else:
        usar_com_mt5()
        print("\n✅ Sistema carregado com sucesso!")
        print("\n📌 COMO USAR:")
        print("""
# Importar
from analise_tecnica_pura import AnalisadorTecnicoPuro

# Criar analisador
analisador = AnalisadorTecnicoPuro()

# Analisar ativo
resultado = analisador.analisar_ativo(
    symbol_info=dados_symbolinfo,
    ativo="SEU_ATIVO",
    operacao="compra"  # ou "venda"
)

# Tomar decisão
if resultado['decisao']['decisao'] == "EXECUTAR":
    print("✅ Operação recomendada!")
        """)



