"""
SISTEMA DE ANÁLISE DE DADOS DO SYMBOLINFO PARA TRADING
Versão: 2.0 - Análise Completa
Autor: Sistema de Análise de Mercado
Data: 2024

Este sistema analisa os dados do SymbolInfo da MT5 para tomada de decisão em trading.
Integra com o sistema de análise de intensidade para decisões mais precisas.

INSTALAÇÃO NECESSÁRIA:
pip install numpy pandas scikit-learn
"""

# ============================================================================
# IMPORTAÇÕES E CONFIGURAÇÕES
# ============================================================================

import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CLASSE PRINCIPAL: ANALISADOR DE SYMBOLINFO
# ============================================================================

class AnalisadorSymbolInfo:
    """Analisa dados do SymbolInfo para tomada de decisão."""
    
    def __init__(self):
        self.historico_analises = []
        self.parametros_ideais = self._definir_parametros_ideais()
        
    def _definir_parametros_ideais(self):
        """Define parâmetros ideais para diferentes tipos de ativos."""
        return {
            'spread_max': {
                'acao_br': 15,      # Spread máximo para ações brasileiras (pontos)
                'acao_us': 5,       # Spread máximo para ações americanas
                'opcao': 30,        # Spread máximo para opções
                'indice': 10,       # Spread máximo para índices
            },
            'volume_min': {
                'acao_br': 10000,   # Volume mínimo para ações brasileiras
                'acao_us': 5000,    # Volume mínimo para ações americanas
                'opcao': 1000,      # Volume mínimo para opções
                'indice': 5000,     # Volume mínimo para índices
            },
            'spread_percentual_max': 0.1,  # Spread máximo em % do preço
            'liquidez_minima': 0.7,        # Nível mínimo de liquidez (0-1)
            'volatilidade_media': 2.0,     # Volatilidade média aceitável (%)
        }
    
    def analisar_symbol_info(self, symbol_info, ativo=None):
        """
        Analisa os dados do SymbolInfo e retorna insights.
        
        Args:
            symbol_info: Objeto SymbolInfo da MT5
            ativo: Nome do ativo (opcional)
        
        Returns:
            Dicionário com análise completa
        """
        try:
            # Converter para dicionário se necessário
            if hasattr(symbol_info, '_asdict'):
                dados = symbol_info._asdict()
            elif isinstance(symbol_info, dict):
                dados = symbol_info
            else:
                # Tentar extrair atributos
                dados = {}
                for attr in dir(symbol_info):
                    if not attr.startswith('_'):
                        try:
                            dados[attr] = getattr(symbol_info, attr)
                        except:
                            pass
            
            #print(f"\n{'='*70}")
            #print(f"📊 ANÁLISE TÉCNICA DO AATIVO: {ativo if ativo else 'Desconhecido'}")
            #print(f"{'='*70}")
            
            # 1. Análise Básica de Preços
            #print("\n💰 ANÁLISE DE PREÇOS:")
            analise_precos = self._analisar_precos(dados)
            #for chave, valor in analise_precos.items():
            #    print(f"   {chave}: {valor}")
            
            # 2. Análise de Spread e Liquidez
            #print("\n📈 ANÁLISE DE LIQUIDEZ:")
            analise_liquidez = self._analisar_liquidez(dados, ativo)
            #for chave, valor in analise_liquidez.items():
            #    if chave != 'recomendacao_liquidez':
            #        print(f"   {chave}: {valor}")
            
            # 3. Análise de Volume
            #print("\n📊 ANÁLISE DE VOLUME:")
            analise_volume = self._analisar_volume(dados, ativo)
            #for chave, valor in analise_volume.items():
            #    if chave != 'recomendacao_volume':
            #        print(f"   {chave}: {valor}")
            
            # 4. Análise de Tendência
            #print("\n📉 ANÁLISE DE TENDÊNCIA:")
            analise_tendencia = self._analisar_tendencia(dados)
            #for chave, valor in analise_tendencia.items():
            #    if chave != 'recomendacao_tendencia':
            #        print(f"   {chave}: {valor}")
            
            # 5. Análise de Risco
            #print("\n⚠️ ANÁLISE DE RISCO:")
            analise_risco = self._analisar_risco(dados)
            #for chave, valor in analise_risco.items():
            #    if chave != 'recomendacao_risco':
            #        print(f"   {chave}: {valor}")
            
            # 6. Recomendação Geral
            #print("\n🎯 RECOMENDAÇÃO GERAL:")
            recomendacao_geral = self._gerar_recomendacao_geral(
                analise_liquidez, analise_volume, analise_tendencia, analise_risco
            )
            
            #print(f"\n{'='*70}")
            print(f"✅ DECISÃO: {recomendacao_geral['decisao']}")
            #print(f"📊 Confiança: {recomendacao_geral['confianca']:.1%}")
            #print(f"💡 Motivo: {recomendacao_geral['motivo']}")
            #print(f"{'='*70}")
            
            # Consolidar análise
            analise_completa = {
                'timestamp': datetime.now(),
                'ativo': ativo,
                'dados': dados,
                'analise_precos': analise_precos,
                'analise_liquidez': analise_liquidez,
                'analise_volume': analise_volume,
                'analise_tendencia': analise_tendencia,
                'analise_risco': analise_risco,
                'recomendacao_geral': recomendacao_geral,
                'pontuacao_total': recomendacao_geral['pontuacao']
            }
            
            # Adicionar ao histórico
            self.historico_analises.append(analise_completa)
            
            return analise_completa
            
        except Exception as e:
            print(f"⚠️ Erro na análise do SymbolInfo: {e}")
            return {
                'erro': str(e),
                'ativo': ativo,
                'recomendacao': {
                    'decisao': 'ANÁLISE_INCOMPLETA',
                    'confianca': 0.0,
                    'motivo': f'Erro na análise: {e}'
                }
            }
    
    def _analisar_precos(self, dados):
        """Analisa os dados de preço do ativo."""
        try:
            bid = dados.get('bid', 0)
            ask = dados.get('ask', 0)
            last = dados.get('last', 0)
            bidhigh = dados.get('bidhigh', 0)
            bidlow = dados.get('bidlow', 0)
            
            # Calcular preço médio
            if bid > 0 and ask > 0:
                preco_medio = (bid + ask) / 2
            else:
                preco_medio = last if last > 0 else 0
            
            # Calcular faixa de preço do dia
            amplitude_dia = bidhigh - bidlow if bidhigh > 0 and bidlow > 0 else 0
            amplitude_percentual = (amplitude_dia / bidlow * 100) if bidlow > 0 else 0
            
            # Preço atual vs faixa do dia
            if bidlow > 0 and bidhigh > bidlow:
                posicao_na_faixa = (bid - bidlow) / (bidhigh - bidlow) * 100
            else:
                posicao_na_faixa = 50
            
            return {
                'Bid': f"{bid:.2f}",
                'Ask': f"{ask:.2f}",
                'Último': f"{last:.2f}",
                'Preço Médio': f"{preco_medio:.2f}",
                'Alta do Dia': f"{bidhigh:.2f}",
                'Baixa do Dia': f"{bidlow:.2f}",
                'Amplitude Diária': f"{amplitude_dia:.2f} ({amplitude_percentual:.2f}%)",
                'Posição na Faixa': f"{posicao_na_faixa:.1f}%",
                'Interpretação Preço': self._interpretar_posicao_preco(posicao_na_faixa)
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de preços: {e}")
            return {'Erro': f'Erro na análise de preços: {e}'}
    
    def _interpretar_posicao_preco(self, posicao_na_faixa):
        """Interpreta a posição do preço na faixa do dia."""
        if posicao_na_faixa < 20:
            return "Próximo da BAIXA do dia - Possível suporte"
        elif posicao_na_faixa < 40:
            return "Na parte INFERIOR da faixa"
        elif posicao_na_faixa < 60:
            return "No MEIO da faixa - Neutro"
        elif posicao_na_faixa < 80:
            return "Na parte SUPERIOR da faixa"
        else:
            return "Próximo da ALTA do dia - Possível resistência"
    
    def _analisar_liquidez(self, dados, ativo):
        """Analisa a liquidez do ativo."""
        try:
            spread = dados.get('spread', 0)
            ask = dados.get('ask', 1)
            bid = dados.get('bid', 1)
            
            # Calcular spread em pontos e percentual
            spread_pontos = spread
            spread_percentual = ((ask - bid) / bid * 100) if bid > 0 else 0
            
            # Determinar tipo de ativo para parâmetros ideais
            tipo_ativo = self._identificar_tipo_ativo(ativo, dados)
            
            # Obter parâmetros ideais para este tipo
            spread_max_ideal = self.parametros_ideais['spread_max'].get(tipo_ativo, 20)
            
            # Avaliar liquidez baseada no spread
            if spread_pontos <= spread_max_ideal * 0.5:
                qualidade_spread = "EXCELENTE"
                pontuacao_spread = 10
            elif spread_pontos <= spread_max_ideal:
                qualidade_spread = "BOA"
                pontuacao_spread = 7
            elif spread_pontos <= spread_max_ideal * 1.5:
                qualidade_spread = "REGULAR"
                pontuacao_spread = 5
            else:
                qualidade_spread = "RUIM"
                pontuacao_spread = 2
            
            # Avaliar spread percentual
            if spread_percentual <= 0.05:
                qualidade_spread_percentual = "EXCELENTE"
                pontuacao_spread_percentual = 10
            elif spread_percentual <= 0.1:
                qualidade_spread_percentual = "BOA"
                pontuacao_spread_percentual = 7
            elif spread_percentual <= 0.2:
                qualidade_spread_percentual = "REGULAR"
                pontuacao_spread_percentual = 5
            else:
                qualidade_spread_percentual = "RUIM"
                pontuacao_spread_percentual = 2
            
            # Pontuação total de liquidez
            pontuacao_total = (pontuacao_spread + pontuacao_spread_percentual) / 2
            
            # Recomendação
            if pontuacao_total >= 8:
                recomendacao = "✅ Alta liquidez - Ótimo para operar"
            elif pontuacao_total >= 6:
                recomendacao = "⚠️ Liquidez moderada - Operar com cautela"
            else:
                recomendacao = "⛔ Baixa liquidez - Evitar operações"
            
            return {
                'Spread (pontos)': f"{spread_pontos}",
                'Spread (%)': f"{spread_percentual:.4f}%",
                'Qualidade Spread': qualidade_spread,
                'Qualidade Spread %': qualidade_spread_percentual,
                'Tipo Ativo Identificado': tipo_ativo,
                'Spread Máximo Ideal': f"{spread_max_ideal} pontos",
                'Pontuação Liquidez': f"{pontuacao_total:.1f}/10",
                'recomendacao_liquidez': recomendacao,
                'pontuacao_liquidez': pontuacao_total
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de liquidez: {e}")
            return {'Erro': f'Erro na análise de liquidez: {e}'}
    
    def _identificar_tipo_ativo(self, ativo, dados):
        """Identifica o tipo de ativo baseado no nome e dados."""
        if not ativo:
            return 'acao_br'  # Padrão
        
        ativo_upper = ativo.upper()
        
        # Verificar por padrões no nome
        if 'H' in ativo_upper and any(c.isdigit() for c in ativo_upper):
            return 'opcao'
        elif any(x in ativo_upper for x in ['WIN', 'WDO', 'DOL', 'IND']):
            return 'indice'
        elif any(x in ativo_upper for x in ['.SA', '.US']):
            if '.US' in ativo_upper:
                return 'acao_us'
            else:
                return 'acao_br'
        elif len(ativo_upper) <= 5 and ativo_upper.isalpha():
            return 'acao_br'
        else:
            # Tentar identificar pela descrição
            descricao = dados.get('description', '').upper()
            if 'ON' in descricao or 'PN' in descricao or 'UNT' in descricao:
                return 'acao_br'
            elif 'CALL' in descricao or 'PUT' in descricao:
                return 'opcao'
            else:
                return 'acao_br'
    
    def _analisar_volume(self, dados, ativo):
        """Analisa o volume e atividade do ativo."""
        try:
            volume = dados.get('volume', 0)
            volume_real = dados.get('volume_real', 0)
            session_volume = dados.get('session_volume', 0)
            volume_min = dados.get('volume_min', 100)
            volume_max = dados.get('volume_max', 0)
            
            # Usar o maior volume disponível
            volume_efetivo = max(volume, volume_real, session_volume)
            
            # Identificar tipo de ativo
            tipo_ativo = self._identificar_tipo_ativo(ativo, dados)
            volume_min_ideal = self.parametros_ideais['volume_min'].get(tipo_ativo, 1000)
            
            # Calcular relação volume atual vs mínimo
            if volume_min_ideal > 0:
                relacao_volume = volume_efetivo / volume_min_ideal
            else:
                relacao_volume = 1
            
            # Avaliar volume
            if volume_efetivo <= 0:
                qualidade_volume = "SEM VOLUME"
                pontuacao_volume = 0
            elif relacao_volume >= 10:
                qualidade_volume = "ALTÍSSIMO"
                pontuacao_volume = 10
            elif relacao_volume >= 5:
                qualidade_volume = "ALTO"
                pontuacao_volume = 8
            elif relacao_volume >= 2:
                qualidade_volume = "MODERADO"
                pontuacao_volume = 6
            elif relacao_volume >= 1:
                qualidade_volume = "BAIXO"
                pontuacao_volume = 4
            else:
                qualidade_volume = "MUITO BAIXO"
                pontuacao_volume = 2
            
            # Análise de faixa de volume
            if volume_max > volume_min:
                posicao_volume = (volume_efetivo - volume_min) / (volume_max - volume_min) * 100
                if posicao_volume > 0:
                    posicao_volume = min(100, posicao_volume)
            else:
                posicao_volume = 50
            
            # Recomendação baseada no volume
            if pontuacao_volume >= 8:
                recomendacao = "✅ Volume excelente - Boa execução esperada"
            elif pontuacao_volume >= 6:
                recomendacao = "⚠️ Volume moderado - Pode haver slippage"
            elif pontuacao_volume >= 4:
                recomendacao = "⚠️ Volume baixo - Risco de execução"
            else:
                recomendacao = "⛔ Volume muito baixo - Evitar operação"
            
            return {
                'Volume Atual': f"{volume_efetivo:,.0f}",
                'Volume Mínimo': f"{volume_min:,.0f}",
                'Volume Máximo': f"{volume_max:,.0f}",
                'Relação Volume': f"{relacao_volume:.1f}x mínimo",
                'Qualidade Volume': qualidade_volume,
                'Posição na Faixa': f"{posicao_volume:.1f}%",
                'Pontuação Volume': f"{pontuacao_volume:.1f}/10",
                'recomendacao_volume': recomendacao,
                'pontuacao_volume': pontuacao_volume
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de volume: {e}")
            return {'Erro': f'Erro na análise de volume: {e}'}
    
    def _analisar_tendencia(self, dados):
        """Analisa a tendência do ativo."""
        try:
            price_change = dados.get('price_change', 0)
            bid = dados.get('bid', 0)
            price_prev = dados.get('price_prev', 0)
            
            # Calcular variação percentual
            if price_prev > 0:
                variacao_percentual = (price_change / price_prev) * 100
            elif bid > 0:
                # Tentar estimar com base em outros dados
                lasthigh = dados.get('lasthigh', 0)
                lastlow = dados.get('lastlow', 0)
                if lasthigh > 0 and lastlow > 0:
                    variacao_percentual = ((bid - lastlow) / lastlow) * 100
                else:
                    variacao_percentual = 0
            else:
                variacao_percentual = 0
            
            # Determinar força da tendência
            abs_variacao = abs(variacao_percentual)
            
            if abs_variacao > 5:
                forca_tendencia = "FORTE"
                pontuacao_tendencia = 8 if variacao_percentual > 0 else 2
            elif abs_variacao > 2:
                forca_tendencia = "MODERADA"
                pontuacao_tendencia = 7 if variacao_percentual > 0 else 3
            elif abs_variacao > 0.5:
                forca_tendencia = "FRACA"
                pontuacao_tendencia = 6 if variacao_percentual > 0 else 4
            else:
                forca_tendencia = "LATERAL"
                pontuacao_tendencia = 5
            
            # Direção da tendência
            if variacao_percentual > 0.5:
                direcao = "ALTA"
                recomendacao = "📈 Tendência de alta"
            elif variacao_percentual < -0.5:
                direcao = "BAIXA"
                recomendacao = "📉 Tendência de baixa"
            else:
                direcao = "NEUTRA"
                recomendacao = "➡️ Mercado lateralizado"
            
            # Análise de volatilidade
            price_volatility = dados.get('price_volatility', 0)
            if price_volatility > 5:
                volatilidade = "ALTA"
            elif price_volatility > 2:
                volatilidade = "MODERADA"
            else:
                volatilidade = "BAIXA"
            
            return {
                'Variação Absoluta': f"{price_change:.3f}",
                'Variação Percentual': f"{variacao_percentual:.2f}%",
                'Direção': direcao,
                'Força Tendência': forca_tendencia,
                'Volatilidade': volatilidade,
                'Pontuação Tendência': f"{pontuacao_tendencia:.1f}/10",
                'recomendacao_tendencia': recomendacao,
                'pontuacao_tendencia': pontuacao_tendencia,
                'variacao_real': variacao_percentual
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de tendência: {e}")
            return {'Erro': f'Erro na análise de tendência: {e}'}
    
    def _analisar_risco(self, dados):
        """Analisa os riscos do ativo."""
        try:
            fatores_risco = []
            pontuacao_risco = 10  # Começa com 10, subtrai por riscos
            
            # 1. Risco de Spread Alto
            spread = dados.get('spread', 0)
            if spread > 20:
                fatores_risco.append("Spread muito alto")
                pontuacao_risco -= 3
            elif spread > 10:
                fatores_risco.append("Spread elevado")
                pontuacao_risco -= 2
            
            # 2. Risco de Volume Baixo
            volume = dados.get('volume', 0)
            if volume < 1000:
                fatores_risco.append("Volume muito baixo")
                pontuacao_risco -= 3
            elif volume < 5000:
                fatores_risco.append("Volume baixo")
                pontuacao_risco -= 1
            
            # 3. Risco de Volatilidade
            price_volatility = dados.get('price_volatility', 0)
            if price_volatility > 10:
                fatores_risco.append("Volatilidade extremamente alta")
                pontuacao_risco -= 3
            elif price_volatility > 5:
                fatores_risco.append("Alta volatilidade")
                pontuacao_risco -= 2
            
            # 4. Risco de Horário (se disponível)
            time = dados.get('time', 0)
            if time > 0:
                # Converter timestamp para hora
                hora = datetime.fromtimestamp(time).hour
                if hora < 10 or hora > 16:  # Fora do horário principal
                    fatores_risco.append("Fora do horário de maior liquidez")
                    pontuacao_risco -= 1
            
            # 5. Risco de Gaps
            session_open = dados.get('session_open', 0)
            last = dados.get('last', 0)
            if session_open > 0 and last > 0:
                gap_percentual = abs((last - session_open) / session_open * 100)
                if gap_percentual > 5:
                    fatores_risco.append(f"Gap de abertura grande ({gap_percentual:.1f}%)")
                    pontuacao_risco -= 2
            
            # Classificação do risco
            if pontuacao_risco >= 8:
                classificacao_risco = "BAIXO"
                recomendacao = "✅ Risco controlado"
            elif pontuacao_risco >= 6:
                classificacao_risco = "MODERADO"
                recomendacao = "⚠️ Risco moderado - Operar com cautela"
            elif pontuacao_risco >= 4:
                classificacao_risco = "ALTO"
                recomendacao = "⚠️ Risco alto - Reduzir tamanho da operação"
            else:
                classificacao_risco = "MUITO ALTO"
                recomendacao = "⛔ Risco muito alto - Evitar operação"
            
            # Garantir pontuação entre 0 e 10
            pontuacao_risco = max(0, min(10, pontuacao_risco))
            
            return {
                'Fatores de Risco': ", ".join(fatores_risco) if fatores_risco else "Nenhum identificado",
                'Classificação Risco': classificacao_risco,
                'Pontuação Risco': f"{pontuacao_risco:.1f}/10",
                'recomendacao_risco': recomendacao,
                'pontuacao_risco': pontuacao_risco,
                'num_fatores_risco': len(fatores_risco)
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de risco: {e}")
            return {'Erro': f'Erro na análise de risco: {e}'}
    
    def _gerar_recomendacao_geral(self, liquidez, volume, tendencia, risco):
        """Gera recomendação geral baseada em todas as análises."""
        try:
            # Extrair pontuações
            p_liquidez = liquidez.get('pontuacao_liquidez', 5)
            p_volume = volume.get('pontuacao_volume', 5)
            p_tendencia = tendencia.get('pontuacao_tendencia', 5)
            p_risco = risco.get('pontuacao_risco', 5)
            
            # Ponderar as pontuações
            pontuacao_total = (
                p_liquidez * 0.25 +      # Liquidez é muito importante
                p_volume * 0.20 +        # Volume também importante
                p_tendencia * 0.30 +     # Tendência é crucial para decisão
                p_risco * 0.25           # Risco deve ser considerado
            )
            
            # Ajustar baseado em fatores críticos
            if p_liquidez < 3 or p_volume < 3:
                pontuacao_total *= 0.7  # Penalidade forte por baixa liquidez/volume
            
            if p_risco < 3:
                pontuacao_total *= 0.8  # Penalidade por alto risco
            
            # Garantir pontuação entre 0 e 10
            pontuacao_total = max(0, min(10, pontuacao_total))
            
            # Gerar recomendação baseada na pontuação
            if pontuacao_total >= 8:
                decisao = "EXECUTAR"
                confianca = pontuacao_total / 10
                motivo = "Condições excelentes para operação"
            elif pontuacao_total >= 6.5:
                decisao = "EXECUTAR_COM_CUIDADO"
                confianca = pontuacao_total / 10 * 0.9
                motivo = "Condições boas, mas requer atenção"
            elif pontuacao_total >= 5:
                decisao = "AGUARDAR_MELHOR_OPORTUNIDADE"
                confianca = 0.5
                motivo = "Condições medianas, aguardar melhora"
            elif pontuacao_total >= 3:
                decisao = "EVITAR"
                confianca = 0.3
                motivo = "Condições desfavoráveis"
            else:
                decisao = "BLOQUEAR"
                confianca = 0.1
                motivo = "Condições muito ruins - Alto risco"
            
            # Ajustes específicos baseados em análise
            variacao = tendencia.get('variacao_real', 0)
            if abs(variacao) > 10:  # Movimento muito forte
                motivo += f" | Movimento muito forte ({variacao:.1f}%)"
                if decisao == "EXECUTAR":
                    decisao = "EXECUTAR_COM_CUIDADO"
            
            num_riscos = risco.get('num_fatores_risco', 0)
            if num_riscos > 3:
                motivo += f" | Muitos fatores de risco ({num_riscos})"
                if decisao not in ["EVITAR", "BLOQUEAR"]:
                    decisao = "AGUARDAR_MELHOR_OPORTUNIDADE"
            
            return {
                'decisao': decisao,
                'confianca': confianca,
                'motivo': motivo,
                'pontuacao': pontuacao_total,
                'detalhes': {
                    'liquidez': p_liquidez,
                    'volume': p_volume,
                    'tendencia': p_tendencia,
                    'risco': p_risco
                }
            }
            
        except Exception as e:
            print(f"⚠️ Erro ao gerar recomendação: {e}")
            return {
                'decisao': 'ERRO_ANALISE',
                'confianca': 0.0,
                'motivo': f'Erro na análise: {e}',
                'pontuacao': 0
            }

# ============================================================================
# SISTEMA INTEGRADO: SYMBOLINFO + ANÁLISE DE INTENSIDADE
# ============================================================================

class SistemaDecisaoCompleto:
    """Sistema que integra análise de SymbolInfo com análise de intensidade."""
    
    def __init__(self):
        self.analisador_symbol = AnalisadorSymbolInfo()
        self.historico_decisoes = []
        
    def analisar_operacao_completa(self, ativo, status, resultado_antigo, resultado_novo, symbol_info):
        """
        Analisa operação completa integrando análise de intensidade e SymbolInfo.
        
        Args:
            ativo: Nome do ativo
            status: "compra" ou "venda"
            resultado_antigo: Resultado da análise antiga
            resultado_novo: Resultado da análise nova
            symbol_info: Dados do SymbolInfo
        
        Returns:
            Análise integrada completa
        """
        #print(f"\n{'#'*80}")
        #print(f"🚀 ANÁLISE COMPLETA DE OPERAÇÃO: {ativo} | {status}")
        #print(f"{'#'*80}")
        
        # 1. Análise do SymbolInfo
        #print("\n📈 ETAPA 1: ANÁLISE TÉCNICA DO ATIVO")
        analise_symbol = self.analisador_symbol.analisar_symbol_info(symbol_info, ativo)
        
        # 2. Extrair dados das análises de intensidade
        #print("\n📊 ETAPA 2: ANÁLISE DE INTENSIDADE DO SINAL")
        perc_antigo = resultado_antigo[1] if len(resultado_antigo) > 1 else 0
        perc_novo = resultado_novo[1] if len(resultado_novo) > 1 else 0
        diferenca = abs(perc_antigo - perc_novo)
        
        #print(f"   Percentual Análise Antiga: {perc_antigo:.1f}%")
        #print(f"   Percentual Análise Nova: {perc_novo:.1f}%")
        #print(f"   Diferença: {diferenca:.1f}%")
        
        # 3. Integrar as análises
        #print("\n⚖️ ETAPA 3: INTEGRAÇÃO DAS ANÁLISES")
        decisao_integrada = self._integrar_analises(
            analise_symbol, perc_antigo, perc_novo, status
        )
        
        # 4. Recomendação Final
        #print("\n🎯 ETAPA 4: RECOMENDAÇÃO FINAL INTEGRADA")
        
        #print(f"\n{'='*80}")
        #print(f"✅ DECISÃO FINAL: {decisao_integrada['decisao']}")
        #print(f"📊 Confiança: {decisao_integrada['confianca']:.1%}")
        #print(f"💡 Motivo: {decisao_integrada['motivo']}")
        
        # Mostrar fatores decisivos
        if 'fatores_decisivos' in decisao_integrada:
            #print(f"\n📌 FATORES DECISIVOS:")
            for fator in decisao_integrada['fatores_decisivos']:
                print(f"   • {fator}")
        
        #print(f"{'='*80}")
        
        # Registrar decisão
        registro = {
            'timestamp': datetime.now(),
            'ativo': ativo,
            'status': status,
            'analise_symbol': analise_symbol,
            'resultado_antigo': resultado_antigo,
            'resultado_novo': resultado_novo,
            'decisao_integrada': decisao_integrada
        }
        
        self.historico_decisoes.append(registro)
        
        return registro
    
    def _identificar_tipo_opcao(self, ativo):
        """Identifica se a opção é CALL ou PUT baseado no código do ativo."""
        if not ativo or len(ativo) <= 4:
            return None
        
        letra_opcao = ativo[4].upper()
        if letra_opcao in "ABCDEFGHIJKL":
            return "CALL"
        elif letra_opcao in "MNOPQRSTUVWXYZ":
            return "PUT"
        
        return None
    
    def _integrar_analises(self, analise_symbol, perc_antigo, perc_novo, status):
        """Integra análise do SymbolInfo com análise de intensidade."""
        
        # Extrair dados do SymbolInfo
        decisao_symbol = analise_symbol.get('recomendacao_geral', {})
        pontuacao_symbol = decisao_symbol.get('pontuacao', 5)
        decisao_sym = decisao_symbol.get('decisao', 'AGUARDAR')
        
        # Análise de tendência do SymbolInfo
        tendencia = analise_symbol.get('analise_tendencia', {})
        variacao = tendencia.get('variacao_real', 0)
        direcao_tendencia = tendencia.get('Direção', 'NEUTRA')
        
        # CORREÇÃO: Identificar tipo de opção
        nome =analise_symbol.get('ativo')
        tipo_opcao = self._identificar_tipo_opcao(analise_symbol.get('ativo'))
        

        # Calcular força do sinal
        media_intensidade = (perc_antigo + perc_novo) / 2
        concordancia = 100 - abs(perc_antigo - perc_novo)  # Quanto maior, mais concordam
        
        # Fatores decisivos
        fatores_decisivos = []
        
        # 1. Verificar bloqueio por intensidade
        if perc_novo == 0:
            return {
                'decisao': 'BLOQUEAR',
                'confianca': 0.9,
                'motivo': 'Análise nova bloqueou (contra tendência)',
                'fatores_decisivos': ['Bloqueio da análise nova']
            }
        
        # 2. Verificar concordância entre análises
        if concordancia < 70:
            fatores_decisivos.append(f'Baixa concordância entre análises ({concordancia:.1f}%)')
        
        # 3. CORREÇÃO: Verificar alinhamento com tendência (lógica corrigida)
        if tipo_opcao == "PUT":
            # Para PUT: compra se beneficia da baixa, venda se beneficia da alta
            if status.lower() == 'compra' and direcao_tendencia == 'BAIXA':
                fatores_decisivos.append(f'✅ Compra de PUT {nome} alinhada com tendência de baixa')
            elif status.lower() == 'compra' and direcao_tendencia == 'ALTA':
                fatores_decisivos.append(f'⚠️ Compra de PUT {nome} contra tendência de alta')
            elif status.lower() == 'venda' and direcao_tendencia == 'ALTA':
                fatores_decisivos.append(f'✅ Venda de PUT {nome} alinhada com tendência de alta')
            elif status.lower() == 'venda' and direcao_tendencia == 'BAIXA':
                fatores_decisivos.append(f'⚠️ Venda de PUT {nome} contra tendência de baixa')
        elif tipo_opcao == "CALL":
            # Para CALL: compra se beneficia da alta, venda se beneficia da baixa
            if status.lower() == 'compra' and direcao_tendencia == 'ALTA':
                fatores_decisivos.append(f'✅ Compra de CALL {nome} alinhada com tendência de alta')
            elif status.lower() == 'compra' and direcao_tendencia == 'BAIXA':
                fatores_decisivos.append(f'⚠️ Compra de CALL contra tendência de baixa')
            elif status.lower() == 'venda' and direcao_tendencia == 'BAIXA':
                fatores_decisivos.append(f'✅ Venda de CALL {nome} alinhada com tendência de baixa')
            elif status.lower() == 'venda' and direcao_tendencia == 'ALTA':
                fatores_decisivos.append(f'⚠️ Venda de CALL {nome} contra tendência de alta')
        else:
            # Para ações ou outros ativos
            if status.lower() == 'compra' and direcao_tendencia == 'BAIXA':
                fatores_decisivos.append('⚠️ Compra contra tendência de baixa')
            elif status.lower() == 'venda' and direcao_tendencia == 'ALTA':
                fatores_decisivos.append('⚠️ Venda contra tendência de alta')
        
        # 4. Pontuação do SymbolInfo
        if pontuacao_symbol < 5:
            fatores_decisivos.append(f'Pontuação técnica baixa ({pontuacao_symbol:.1f}/10)')
        
        # Calcular pontuação integrada
        peso_intensidade = 0.4
        peso_symbol = 0.4
        peso_concordancia = 0.2
        
        pontuacao_int = media_intensidade / 10  # Converter para escala 0-10
        pontuacao_conc = concordancia / 10
        
        pontuacao_integrada = (
            pontuacao_int * peso_intensidade +
            pontuacao_symbol * peso_symbol +
            pontuacao_conc * peso_concordancia
        )
        
        # Ajustes baseados em fatores críticos
        ajuste = 1.0
        if len(fatores_decisivos) >= 3:
            ajuste *= 0.7  # Penalidade forte
        elif len(fatores_decisivos) >= 2:
            ajuste *= 0.8  # Penalidade moderada
        elif len(fatores_decisivos) >= 1:
            ajuste *= 0.9  # Penalidade leve
        
        pontuacao_final = pontuacao_integrada * ajuste
        
        # Gerar decisão baseada na pontuação
        if pontuacao_final >= 7:
            if decisao_sym == 'EXECUTAR' and media_intensidade >= 60:
                decisao = 'EXECUTAR'
                confianca = min(0.95, pontuacao_final / 10)
                motivo = 'Condições técnicas excelentes e sinal forte'
            else:
                decisao = 'EXECUTAR_COM_CUIDADO'
                confianca = pontuacao_final / 10 * 0.8
                motivo = 'Condições boas, mas com ressalvas'
        
        elif pontuacao_final >= 5:
            decisao = 'AGUARDAR_CONFIRMAÇÃO'
            confianca = 0.5
            motivo = 'Condições medianas, aguardar confirmação'
        
        elif pontuacao_final >= 3:
            decisao = 'EVITAR'
            confianca = 0.3
            motivo = 'Condições desfavoráveis'
        
        else:
            decisao = 'BLOQUEAR'
            confianca = 0.1
            motivo = 'Condições muito ruins'
        
        # Adicionar informações específicas ao motivo
        if variacao != 0:
            sinal_variacao = '+' if variacao > 0 else ''
            motivo += f' | Variação: {sinal_variacao}{variacao:.2f}%'
        
        if media_intensidade > 0:
            motivo += f' | Intensidade média: {media_intensidade:.1f}%'
        
        return {
            'decisao': decisao,
            'confianca': confianca,
            'motivo': motivo,
            'pontuacao_integrada': pontuacao_final,
            'fatores_decisivos': fatores_decisivos,
            'detalhes': {
                'pontuacao_symbol': pontuacao_symbol,
                'media_intensidade': media_intensidade,
                'concordancia': concordancia,
                'direcao_tendencia': direcao_tendencia,
                'variacao': variacao,
                'tipo_opcao': tipo_opcao
            }
        }




# ============================================================================
# FUNÇÕES UTILITÁRIAS E EXEMPLOS
# ============================================================================

def criar_simbolo_exemplo():
    """Cria um exemplo de SymbolInfo para testes."""
    class SimboloExemplo:
        def __init__(self):
            self.custom = False
            self.chart_mode = 1
            self.select = True
            self.visible = True
            self.session_deals = 66256
            self.session_buy_orders = 0
            self.session_sell_orders = 0
            self.volume = 26800
            self.volumehigh = 18647120494
            self.volumelow = 1700
            self.time = 1765309500
            self.digits = 2
            self.spread = 13
            self.spread_float = True
            self.ticks_bookdepth = 32
            self.trade_calc_mode = 32
            self.trade_mode = 4
            self.start_time = 0
            self.expiration_time = 253402300799
            self.trade_stops_level = 0
            self.trade_freeze_level = 0
            self.trade_exemode = 3
            self.swap_mode = 0
            self.swap_rollover3days = 3
            self.margin_hedged_use_leg = False
            self.expiration_mode = 2
            self.filling_mode = 3
            self.order_mode = 127
            self.order_gtc_mode = 0
            self.option_mode = 0
            self.option_right = 0
            self.bid = 69.74
            self.bidhigh = 70.41
            self.bidlow = 68.9
            self.ask = 69.87
            self.askhigh = 70.43
            self.asklow = 68.94
            self.last = 69.87
            self.lasthigh = 70.43
            self.lastlow = 68.9
            self.volume_real = 26800.0
            self.volumehigh_real = 18647120494.23024
            self.volumelow_real = 1700.0
            self.option_strike = 0.0
            self.point = 0.01
            self.trade_tick_value = 0.01
            self.trade_tick_value_profit = 0.01
            self.trade_tick_value_loss = 0.01
            self.trade_tick_size = 0.01
            self.trade_contract_size = 1.0
            self.trade_accrued_interest = 0.0
            self.trade_face_value = 0.0
            self.trade_liquidity_rate = 0.0
            self.volume_min = 100.0
            self.volume_max = 90780151.0
            self.volume_step = 100.0
            self.volume_limit = 0.0
            self.swap_long = 0.0
            self.swap_short = 0.0
            self.margin_initial = 0.0
            self.margin_maintenance = 0.0
            self.session_volume = 23081300.0
            self.session_turnover = 0.0
            self.session_interest = 0.0
            self.session_buy_orders_volume = 0.0
            self.session_sell_orders_volume = 0.0
            self.session_open = 69.78
            self.session_close = 69.78
            self.session_aw = 69.76
            self.session_price_settlement = 0.0
            self.session_price_limit_min = 0.0
            self.session_price_limit_max = 0.0
            self.margin_hedged = 0.0
            self.price_change = 0.129
            self.price_volatility = 0.0
            self.price_theoretical = 0.0
            self.price_greeks_delta = 0.0
            self.price_greeks_theta = 0.0
            self.price_greeks_gamma = 0.0
            self.price_greeks_vega = 0.0
            self.price_greeks_rho = 0.0
            self.price_greeks_omega = 0.0
            self.price_sensitivity = 0.0
            self.basis = ''
            self.category = ''
            self.currency_base = 'BRL'
            self.currency_profit = 'BRL'
            self.currency_margin = 'BRL'
            self.bank = ''
            self.description = 'VALE        ON      NM'
            self.exchange = 'BVMF'
            self.formula = ''
            self.isin = 'BRVALEACNOR0'
            self.name = 'VALE3'
            self.page = ''
            self.path = 'BOVESPA\\A VISTA\\VALE3'
    
    return SimboloExemplo()

def exemplo_analise_completa():
    """Exemplo de análise completa."""
    print("\n" + "="*80)
    print("📚 EXEMPLO DE ANÁLISE COMPLETA COM SYMBOLINFO")
    print("="*80)
    
    # 1. Criar sistema
    sistema = SistemaDecisaoCompleto()
    
    # 2. Dados de exemplo
    ativo = "VALE3"
    status = "compra"
    
    # Resultados das análises de intensidade (simulados)
    resultado_antigo = (
        "COMPRA FORTE (68.0%)\nCompradores: 1500 | Vendedores: 800\n"
        "Principal: VALE3\nPressão Principal: 62.0%\n"
        "✔️ CALL reforçada pela alta do ativo",
        68.0,
        62.0
    )
    
    resultado_novo = (
        "COMPRA FORTE (72.0%)\nForça Bull: 1600 | Força Bear: 700\n"
        "Principal: VALE3\nPressão Principal: 65.0%\n"
        "✔️ Compra reforçada pela alta do ativo (+1.2%)",
        72.0,
        65.0
    )
    
    # SymbolInfo (exemplo)
    symbol_info = criar_simbolo_exemplo()
    
    # 3. Executar análise completa
    print(f"\nAnalisando {ativo} - {status}...")
    analise = sistema.analisar_operacao_completa(
        ativo, status, resultado_antigo, resultado_novo, symbol_info
    )
    
    return analise

# ============================================================================
# USO COM SUAS FUNÇÕES EXISTENTES
# ============================================================================

def analisar_com_symbolinfo(ativo, status, resultado_antigo, resultado_novo, symbol_info):
    """
    Função principal para usar com suas funções existentes.
    
    Exemplo de uso:
    
    # Obter dados do MT5
    symbol_info = mt5.symbol_info("VALE3")
    
    # Suas análises
    resultado_antigo = intensidade_sinal_antiga("VALE3", "compra")
    resultado_novo = intensidade_sinal("VALE3", "compra")
    
    # Análise completa
    analise = analisar_com_symbolinfo("VALE3", "compra", resultado_antigo, resultado_novo, symbol_info)
    
    # Tomar decisão
    if analise['decisao_integrada']['decisao'] == "EXECUTAR":
        print("✅ Operar!")
    """
    sistema = SistemaDecisaoCompleto()
    
    return sistema.analisar_operacao_completa(
        ativo, status, resultado_antigo, resultado_novo, symbol_info
    )

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🤖 SISTEMA DE ANÁLISE COM SYMBOLINFO PARA TRADING")
    print("="*80)
    print("Versão: 2.0 - Análise Completa Integrada")
    print("Recursos: Análise técnica + Intensidade do sinal")
    print("="*80)
    
    # Executar exemplo
    resposta = input("\nDeseja executar o exemplo completo? (s/n): ").strip().lower()
    
    if resposta == 's':
        resultado = exemplo_analise_completa()
        print(f"\n✅ Análise concluída!")
        print(f"📊 Total de decisões no histórico: {len(resultado.get('historico_decisoes', []))}")
    else:
        print("\n✅ Sistema carregado com sucesso!")
        print("\n📌 COMO USAR COM SEU CÓDIGO:")
        print("""
# 1. Importar o sistema
from analise_symbolinfo import analisar_com_symbolinfo

# 2. Obter dados do MT5
symbol_info = mt5.symbol_info("PETR4")

# 3. Executar suas análises
resultado_antigo = intensidade_sinal_antiga("PETR4", "compra")
resultado_novo = intensidade_sinal("PETR4", "compra")

# 4. Análise completa
analise = analisar_com_symbolinfo(
    ativo="PETR4",
    status="compra",
    resultado_antigo=resultado_antigo,
    resultado_novo=resultado_novo,
    symbol_info=symbol_info
)

# 5. Tomar decisão
decisao = analise['decisao_integrada']['decisao']
confianca = analise['decisao_integrada']['confianca']

if decisao in ["EXECUTAR", "EXECUTAR_COM_CUIDADO"]:
    print(f"✅ Operar! Confiança: {confianca:.1%}")
else:
    print(f"⛔ Não operar. Motivo: {analise['decisao_integrada']['motivo']}")
        """)