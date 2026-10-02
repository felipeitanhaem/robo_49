import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from collections import deque

class RedeNeuralOpcoes:
    """
    Sistema de aprendizado por reforço para otimização de sinais de opções
    """
    
    def __init__(self, arquivo_modelo="modelo_opcoes.json"):
        self.arquivo_modelo = arquivo_modelo
        self.memorias = deque(maxlen=500)  # Guarda últimas 500 operações
        
        # Pesos iniciais (serão ajustados)
        self.pesos = {
            'tendencia': 4.0,
            'correlacao': 1.0,
            'velocidade': 3.0,
            'aceleracao': 2.0,
            'momento': 1.5,
            'cruzamento': 1.0
        }
        
        # Thresholds ajustáveis
        self.thresholds = {
            'score_call_forte': 6.0,
            'score_call': 4.0,
            'score_put_forte': -6.0,
            'score_put': -4.0,
            'confianca_minima': 0.60
        }
        
        # Taxa de aprendizado
        self.taxa_aprendizado = 0.01
        self.fator_desconto = 0.9  # Importância de recompensas futuras
        
        # Estatísticas
        self.estatisticas = {
            'total_operacoes': 0,
            'acertos': 0,
            'erros': 0,
            'lucro_total': 0.0,
            'historico_scores': []
        }
        
        # Carregar modelo salvo se existir
        self.carregar_modelo()
    
    # ================== FUNÇÕES PRINCIPAIS ==================
    
    def analisar(self, opcao, dados_mercado):
        """
        Analisa e retorna sinal com pesos ajustados
        """
        # Calcular métricas base (slope, velocidade, etc)
        metricas = self._calcular_metricas(dados_mercado)
        
        # Calcular score com pesos atuais
        score = self._calcular_score(metricas)
        
        # Decisão baseada no score e thresholds
        decisao = self._decidir(score, metricas)
        
        # Guardar estado para aprendizado futuro
        estado = {
            'timestamp': datetime.now(),
            'opcao': opcao,
            'metricas': metricas,
            'score': score,
            'decisao': decisao,
            'preco_entrada': dados_mercado['preco_atual']
        }
        
        return estado
    
    def registrar_resultado(self, estado, lucro_percentual):
        """
        Registra o resultado da operação e ajusta os pesos
        """
        # Calcular recompensa
        recompensa = self._calcular_recompensa(lucro_percentual)
        
        # Guardar na memória
        self.memorias.append({
            'estado': estado,
            'recompensa': recompensa,
            'lucro': lucro_percentual
        })
        
        # Atualizar estatísticas
        self.estatisticas['total_operacoes'] += 1
        self.estatisticas['lucro_total'] += lucro_percentual
        
        if lucro_percentual > 0:
            self.estatisticas['acertos'] += 1
        else:
            self.estatisticas['erros'] += 1
        
        # Aprender com o resultado
        self._aprender(estado, recompensa)
        
        # Salvar modelo atualizado
        self.salvar_modelo()
        
        return recompensa
    
    # ================== FUNÇÕES INTERNAS ==================
    
    def _calcular_metricas(self, dados):
        """
        Calcula todas as métricas necessárias
        """
        rsi = np.array(dados['rsi_list'][-7:])
        ma = np.array(dados['ma_list'][-7:])
        diff = rsi - ma
        
        # 1. Tendência
        x = np.arange(len(diff))
        slope, _ = np.polyfit(x, diff, 1)
        
        # 2. Correlação
        correlacao = np.corrcoef(x, diff)[0, 1] if len(diff) > 1 else 0
        
        # 3. Velocidade
        velocidade = diff[-1] - diff[-2] if len(diff) >= 2 else 0
        velocidade_media = np.mean(np.diff(diff)) if len(diff) > 2 else velocidade
        
        # 4. Aceleração
        if len(diff) >= 3:
            aceleracao = (diff[-1] - diff[-2]) - (diff[-2] - diff[-3])
            aceleracao_media = np.mean(np.diff(np.diff(diff))) if len(diff) > 3 else aceleracao
        else:
            aceleracao = 0
            aceleracao_media = 0
        
        # 5. Momento
        if len(diff) >= 3:
            momento = np.mean(diff[-3:]) - np.mean(diff)
        else:
            momento = 0
        
        # 6. Cruzamento
        cruzamento = 0
        if len(diff) >= 2:
            if diff[-2] < 0 and diff[-1] > 0:
                cruzamento = 1
            elif diff[-2] > 0 and diff[-1] < 0:
                cruzamento = -1
        
        # 7. Volatilidade (para ajuste)
        volatilidade = np.std(diff) if len(diff) > 1 else 0
        
        return {
            'diff': diff,
            'slope': slope,
            'correlacao': correlacao,
            'velocidade': velocidade,
            'velocidade_media': velocidade_media,
            'aceleracao': aceleracao,
            'aceleracao_media': aceleracao_media,
            'momento': momento,
            'cruzamento': cruzamento,
            'volatilidade': volatilidade,
            'diff_atual': diff[-1],
            'diff_anterior': diff[-2] if len(diff) >= 2 else None
        }
    
    def _calcular_score(self, metricas):
        """
        Calcula score usando pesos atuais
        """
        score = 0
        p = self.pesos  # Atalho
        
        # 1. Tendência (peso ajustável)
        slope = metricas['slope']
        if slope > 0.3:
            score += p['tendencia']
        elif slope > 0.15:
            score += p['tendencia'] * 0.75
        elif slope > 0.05:
            score += p['tendencia'] * 0.375
        elif slope < -0.3:
            score -= p['tendencia']
        elif slope < -0.15:
            score -= p['tendencia'] * 0.75
        elif slope < -0.05:
            score -= p['tendencia'] * 0.375
        
        # 2. Correlação (bônus)
        if abs(metricas['correlacao']) > 0.8:
            score += p['correlacao'] if slope > 0 else -p['correlacao']
        
        # 3. Velocidade
        vel = metricas['velocidade']
        if vel > 0.3:
            score += p['velocidade']
        elif vel > 0.15:
            score += p['velocidade'] * 0.67
        elif vel > 0.05:
            score += p['velocidade'] * 0.33
        elif vel < -0.3:
            score -= p['velocidade']
        elif vel < -0.15:
            score -= p['velocidade'] * 0.67
        elif vel < -0.05:
            score -= p['velocidade'] * 0.33
        
        # 4. Aceleração
        acc = metricas['aceleracao']
        if acc > 0.2:
            score += p['aceleracao']
        elif acc > 0.1:
            score += p['aceleracao'] * 0.75
        elif acc > 0.05:
            score += p['aceleracao'] * 0.25
        elif acc < -0.2:
            score -= p['aceleracao']
        elif acc < -0.1:
            score -= p['aceleracao'] * 0.75
        elif acc < -0.05:
            score -= p['aceleracao'] * 0.25
        
        # 5. Momento
        mom = metricas['momento']
        if mom > 0.15:
            score += p['momento']
        elif mom > 0.05:
            score += p['momento'] * 0.5
        elif mom < -0.15:
            score -= p['momento']
        elif mom < -0.05:
            score -= p['momento'] * 0.5
        
        # 6. Cruzamento
        score += metricas['cruzamento'] * p['cruzamento']
        
        return score
    
    def _decidir(self, score, metricas):
        """
        Toma decisão baseada no score e thresholds
        """
        t = self.thresholds
        
        # Calcular confiança
        consistencia = self._calcular_consistencia(metricas)
        
        if score >= t['score_call_forte'] and consistencia > 0.6:
            return {
                'sinal': 'CALL_FORTE',
                'confianca': min(0.95, 0.85 + (score - t['score_call_forte']) * 0.02),
                'motivo': 'tendencia_muito_forte_alta'
            }
        elif score >= t['score_call']:
            confianca = 0.70 + (score - t['score_call']) * 0.05
            return {
                'sinal': 'CALL',
                'confianca': min(0.90, confianca),
                'motivo': 'tendencia_forte_alta'
            }
        elif score <= t['score_put_forte'] and consistencia > 0.6:
            return {
                'sinal': 'PUT_FORTE',
                'confianca': min(0.95, 0.85 + abs(score - t['score_put_forte']) * 0.02),
                'motivo': 'tendencia_muito_forte_baixa'
            }
        elif score <= t['score_put']:
            confianca = 0.70 + abs(score - t['score_put']) * 0.05
            return {
                'sinal': 'PUT',
                'confianca': min(0.90, confianca),
                'motivo': 'tendencia_forte_baixa'
            }
        else:
            return {
                'sinal': 'NEUTRO',
                'confianca': 0.30,
                'motivo': 'sem_tendencia_clara'
            }
    
    def _calcular_consistencia(self, metricas):
        """
        Calcula consistência dos sinais
        """
        sinais = []
        
        # Sinal da tendência
        sinais.append(1 if metricas['slope'] > 0 else -1 if metricas['slope'] < 0 else 0)
        
        # Sinal da velocidade
        sinais.append(1 if metricas['velocidade'] > 0 else -1 if metricas['velocidade'] < 0 else 0)
        
        # Sinal da aceleração
        sinais.append(1 if metricas['aceleracao'] > 0 else -1 if metricas['aceleracao'] < 0 else 0)
        
        # Sinal do momento
        sinais.append(1 if metricas['momento'] > 0 else -1 if metricas['momento'] < 0 else 0)
        
        # Sinal do cruzamento
        sinais.append(metricas['cruzamento'])
        
        # Contar sinais positivos e negativos
        positivos = sum(1 for s in sinais if s > 0)
        negativos = sum(1 for s in sinais if s < 0)
        total = len([s for s in sinais if s != 0])
        
        if total == 0:
            return 0
        
        return abs(positivos - negativos) / total
    
    def _calcular_recompensa(self, lucro_percentual):
        """
        Calcula recompensa baseada no lucro/prejuízo
        """
        if lucro_percentual > 0:
            # Recompensa positiva (crescimento logarítmico para evitar overfitting)
            return np.log(1 + lucro_percentual * 0.1) * 2
        else:
            # Penalidade (exponencial para operações muito ruins)
            return -np.exp(-lucro_percentual * 0.05) * 1.5
    
    def _aprender(self, estado, recompensa):
        """
        Ajusta os pesos usando aprendizado por reforço
        """
        # Extrair informações do estado
        metricas = estado['metricas']
        score = estado['score']
        decisao = estado['decisao']
        
        # Calcular gradiente aproximado para cada peso
        for chave in self.pesos.keys():
            # Tentar aumentar o peso
            self.pesos[chave] += self.taxa_aprendizado
            
            # Recalcular score com novo peso
            novo_score = self._calcular_score(metricas)
            
            # Verificar se a mudança melhorou
            if recompensa > 0:
                # Se operação deu lucro, reforçar pesos que levaram à decisão certa
                if (decisao['sinal'] in ['CALL', 'CALL_FORTE'] and novo_score > score) or \
                   (decisao['sinal'] in ['PUT', 'PUT_FORTE'] and novo_score < score):
                    self.pesos[chave] += self.taxa_aprendizado * 0.5
                else:
                    self.pesos[chave] -= self.taxa_aprendizado * 0.3
            else:
                # Se operação deu prejuízo, reduzir pesos que contribuíram para decisão errada
                if (decisao['sinal'] in ['CALL', 'CALL_FORTE'] and novo_score > score) or \
                   (decisao['sinal'] in ['PUT', 'PUT_FORTE'] and novo_score < score):
                    self.pesos[chave] -= self.taxa_aprendizado * 0.5
                else:
                    self.pesos[chave] += self.taxa_aprendizado * 0.3
            
            # Restaurar valor original
            self.pesos[chave] -= self.taxa_aprendizado
            
            # Aplicar mudança final com fator de desconto
            self.pesos[chave] += self.taxa_aprendizado * recompensa * 0.1
        
        # Ajustar thresholds também
        if recompensa > 0:
            # Se lucro, manter thresholds (estão funcionando)
            pass
        else:
            # Se prejuízo, ajustar thresholds para serem mais conservadores
            self.thresholds['score_call'] += self.taxa_aprendizado * 0.1
            self.thresholds['score_put'] -= self.taxa_aprendizado * 0.1
            self.thresholds['confianca_minima'] += self.taxa_aprendizado * 0.05
        
        # Normalizar pesos para evitar explosão
        self._normalizar_pesos()
        
        # Guardar score no histórico
        self.estatisticas['historico_scores'].append(score)
    
    def _normalizar_pesos(self):
        """
        Normaliza pesos para manter proporções
        """
        total = sum(self.pesos.values())
        if total > 0:
            for chave in self.pesos:
                self.pesos[chave] = (self.pesos[chave] / total) * 12  # Média ~2
    
    # ================== PERSISTÊNCIA ==================
    
    def salvar_modelo(self):
        """
        Salva o modelo em arquivo JSON
        """
        modelo = {
            'pesos': self.pesos,
            'thresholds': self.thresholds,
            'estatisticas': self.estatisticas,
            'taxa_aprendizado': self.taxa_aprendizado,
            'data_atualizacao': datetime.now().isoformat()
        }
        
        try:
            with open(self.arquivo_modelo, 'w') as f:
                json.dump(modelo, f, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar modelo: {e}")
            return False
    
    def carregar_modelo(self):
        """
        Carrega modelo salvo
        """
        if not os.path.exists(self.arquivo_modelo):
            print("Nenhum modelo salvo encontrado. Usando configurações padrão.")
            return False
        
        try:
            with open(self.arquivo_modelo, 'r') as f:
                modelo = json.load(f)
            
            self.pesos = modelo.get('pesos', self.pesos)
            self.thresholds = modelo.get('thresholds', self.thresholds)
            self.estatisticas = modelo.get('estatisticas', self.estatisticas)
            self.taxa_aprendizado = modelo.get('taxa_aprendizado', self.taxa_aprendizado)
            
            print(f"✅ Modelo carregado: {self.estatisticas['total_operacoes']} operações")
            return True
        except Exception as e:
            print(f"Erro ao carregar modelo: {e}")
            return False
    
    def get_estatisticas(self):
        """
        Retorna estatísticas de desempenho
        """
        total = self.estatisticas['total_operacoes']
        if total == 0:
            return {
                'taxa_acerto': 0,
                'lucro_medio': 0,
                'total_operacoes': 0
            }
        
        return {
            'taxa_acerto': self.estatisticas['acertos'] / total * 100,
            'lucro_medio': self.estatisticas['lucro_total'] / total,
            'total_operacoes': total,
            'acertos': self.estatisticas['acertos'],
            'erros': self.estatisticas['erros'],
            'lucro_total': self.estatisticas['lucro_total']
        }
    
    def resetar_modelo(self):
        """
        Reseta modelo para configurações iniciais
        """
        self.pesos = {
            'tendencia': 4.0,
            'correlacao': 1.0,
            'velocidade': 3.0,
            'aceleracao': 2.0,
            'momento': 1.5,
            'cruzamento': 1.0
        }
        self.thresholds = {
            'score_call_forte': 6.0,
            'score_call': 4.0,
            'score_put_forte': -6.0,
            'score_put': -4.0,
            'confianca_minima': 0.60
        }
        self.estatisticas = {
            'total_operacoes': 0,
            'acertos': 0,
            'erros': 0,
            'lucro_total': 0.0,
            'historico_scores': []
        }
        self.memorias.clear()
        self.salvar_modelo()