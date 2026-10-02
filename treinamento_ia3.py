import json
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import ast
import copy

class TreinadorCompativel:
    def __init__(self, arquivo_modelo='modelo_opcoes.json', arquivo_dados='finalizados.json'):
        self.arquivo_modelo = arquivo_modelo
        self.arquivo_dados = arquivo_dados
        self.modelo_atual = None
        self.dados = None
        self.metricas_extraidas = []
        self.features_originais = ['tendencia', 'correlacao', 'velocidade', 'aceleracao', 'momento', 'cruzamento']
        
        self.carregar_modelo()
        self.carregar_dados()
    
    def carregar_modelo(self):
        """Carrega o modelo mantendo a estrutura exata"""
        try:
            with open(self.arquivo_modelo, 'r', encoding='utf-8') as f:
                self.modelo_atual = json.load(f)
            
            print(f"✅ Modelo carregado: {self.arquivo_modelo}")
            print(f"  Pesos: {len(self.modelo_atual.get('pesos', {}))} features")
            print(f"  Operações: {self.modelo_atual.get('estatisticas', {}).get('total_operacoes', 0)}")
            
            # Verifica estrutura
            pesos = self.modelo_atual.get('pesos', {})
            pesos_esperados = ['tendencia', 'correlacao', 'velocidade', 'aceleracao', 'momento', 'cruzamento']
            
            for peso in pesos_esperados:
                if peso not in pesos:
                    print(f"⚠️ Peso '{peso}' não encontrado. Adicionando padrão...")
                    pesos[peso] = 1.0
            
            return self.modelo_atual
            
        except FileNotFoundError:
            print(f"⚠️ Arquivo {self.arquivo_modelo} não encontrado. Criando novo...")
            self.modelo_atual = self.criar_modelo_padrao()
            return self.modelo_atual
    
    def criar_modelo_padrao(self):
        """Cria modelo com estrutura exata do original"""
        return {
            "pesos": {
                "tendencia": 3.0,
                "correlacao": 1.0,
                "velocidade": 2.5,
                "aceleracao": 1.8,
                "momento": 1.5,
                "cruzamento": 1.0
            },
            "thresholds": {
                "score_call_forte": 6.0,
                "score_call": 4.0,
                "score_put_forte": -6.0,
                "score_put": -4.0,
                "confianca_minima": 0.6
            },
            "estatisticas": {
                "total_operacoes": 0,
                "acertos": 0,
                "erros": 0,
                "lucro_total": 0,
                "historico_scores": []
            },
            "taxa_aprendizado": 0.01,
            "data_atualizacao": datetime.now().isoformat()
        }
    
    def carregar_dados(self):
        """Carrega dados das operações"""
        try:
            with open(self.arquivo_dados, 'r', encoding='utf-8') as f:
                dados_raw = json.load(f)
            
            self.dados = []
            for id_op, op in dados_raw.items():
                op['id'] = id_op
                self.dados.append(op)
            
            print(f"✅ Dados carregados: {len(self.dados)} operações")
            self.extrair_metricas()
            return self.dados
            
        except FileNotFoundError:
            print(f"❌ Arquivo {self.arquivo_dados} não encontrado!")
            return None
    
    def extrair_metricas(self):
        """Extrai métricas do ia_estado"""
        self.metricas_extraidas = []
        
        for op in self.dados:
            ia_estado = op.get('ia_estado', {})
            
            if isinstance(ia_estado, str):
                try:
                    ia_estado = json.loads(ia_estado)
                except:
                    try:
                        ia_estado = ast.literal_eval(ia_estado)
                    except:
                        ia_estado = {}
            
            if isinstance(ia_estado, dict):
                metricas = ia_estado.get('metricas', {})
                score = ia_estado.get('score', 0)
                decisao = ia_estado.get('decisao', {})
                
                lucro_correto = self.calcular_lucro_correto(op)
                
                self.metricas_extraidas.append({
                    'id': op.get('id'),
                    'score': score,
                    'sinal': decisao.get('sinal', 'NEUTRO'),
                    'confianca': decisao.get('confianca', 0.3),
                    'lucro_percentual': lucro_correto,
                    'r_fim': op.get('r_fim', 0),
                    'tipo': op.get('tipo', ''),
                    'entrada': op.get('entrada', 0),
                    'qtd': op.get('qtd', 0),
                    **metricas
                })
        
        print(f"✅ Métricas extraídas: {len(self.metricas_extraidas)}")
        return self.metricas_extraidas
    
    def calcular_lucro_correto(self, operacao):
        entrada = operacao.get('entrada', 0)
        qtd = operacao.get('qtd', 0)
        r_fim = operacao.get('r_fim', 0)
        
        if entrada == 0 or qtd == 0:
            return 0
        
        valor_total = entrada * qtd
        lucro_percentual = (r_fim / valor_total) * 100
        return round(lucro_percentual, 2)
    
    def otimizar_pesos(self):
        """
        Otimiza pesos MANTENDO a estrutura original
        Apenas as 6 features originais são atualizadas
        """
        if not self.metricas_extraidas:
            print("❌ Nenhuma métrica disponível")
            return self.modelo_atual['pesos']
        
        df = pd.DataFrame(self.metricas_extraidas)
        df['lucrativo'] = (df['lucro_percentual'] > 0).astype(int)
        
        # Mapeamento APENAS das features originais
        mapeamento = {
            'slope': 'tendencia',
            'correlacao': 'correlacao',
            'velocidade': 'velocidade',
            'aceleracao': 'aceleracao',
            'momento': 'momento',
            'volatilidade': 'cruzamento'
        }
        
        # Features disponíveis
        features_para_treino = []
        for feature in mapeamento.keys():
            if feature in df.columns:
                features_para_treino.append(feature)
        
        if len(features_para_treino) < 3:
            print("⚠️ Features insuficientes, mantendo pesos atuais")
            return self.modelo_atual['pesos']
        
        # Prepara dados
        X = df[features_para_treino].fillna(0)
        y = df['lucrativo']
        
        # Treina modelo simples
        try:
            modelo = LogisticRegression(max_iter=1000, random_state=42)
            modelo.fit(X, y)
            
            # Coeficientes
            coeficientes = modelo.coef_[0]
            
            # Mapeia para pesos
            pesos_otimizados = {}
            for i, feature in enumerate(features_para_treino):
                if feature in mapeamento:
                    nome_peso = mapeamento[feature]
                    # Normaliza e garante valores positivos
                    peso = np.tanh(coeficientes[i]) * 5  # Escala menor para estabilidade
                    
                    # Força valores positivos para todas as features originais
                    if nome_peso in ['tendencia', 'correlacao', 'velocidade', 'aceleracao', 'momento', 'cruzamento']:
                        peso = abs(peso)  # GARANTE POSITIVO!
                    
                    # Limita para não ficar extremo
                    peso = max(0.1, min(10.0, peso))
                    pesos_otimizados[nome_peso] = round(peso, 4)
            
            # Garante que todos os pesos existam
            pesos_originais = self.modelo_atual['pesos']
            for key in pesos_originais.keys():
                if key not in pesos_otimizados:
                    pesos_otimizados[key] = pesos_originais[key]
            
            # Garante ordem correta
            pesos_finais = {}
            for key in ['tendencia', 'correlacao', 'velocidade', 'aceleracao', 'momento', 'cruzamento']:
                pesos_finais[key] = pesos_otimizados.get(key, pesos_originais.get(key, 1.0))
            
            print(f"\n⚖️ Pesos Otimizados (mantendo estrutura):")
            for key, value in pesos_finais.items():
                print(f"  {key}: {value:.4f}")
            
            return pesos_finais
            
        except Exception as e:
            print(f"⚠️ Erro no treinamento: {e}")
            return self.modelo_atual['pesos']
    
    def otimizar_thresholds(self):
        """
        Otimiza thresholds mantendo valores razoáveis
        """
        if not self.metricas_extraidas:
            return self.modelo_atual['thresholds']
        
        df = pd.DataFrame(self.metricas_extraidas)
        df['lucrativo'] = df['lucro_percentual'] > 0
        
        scores_lucro = df[df['lucrativo']]['score'].values
        scores_prejuizo = df[~df['lucrativo']]['score'].values
        
        if len(scores_lucro) == 0 or len(scores_prejuizo) == 0:
            return self.modelo_atual['thresholds']
        
        # Calcula thresholds
        thresholds = {
            'score_call_forte': round(np.percentile(scores_lucro, 70), 2) if len(scores_lucro) > 0 else 6.0,
            'score_call': round(np.percentile(scores_lucro, 50), 2) if len(scores_lucro) > 0 else 4.0,
            'score_put_forte': round(np.percentile(scores_prejuizo, 30), 2) if len(scores_prejuizo) > 0 else -6.0,
            'score_put': round(np.percentile(scores_prejuizo, 50), 2) if len(scores_prejuizo) > 0 else -4.0,
            'confianca_minima': round(np.mean(df['confianca']) * 0.7, 4)
        }
        
        # Limita para valores razoáveis
        thresholds['score_call_forte'] = max(4.0, min(8.0, thresholds['score_call_forte']))
        thresholds['score_call'] = max(2.0, min(6.0, thresholds['score_call']))
        thresholds['score_put_forte'] = min(-4.0, max(-10.0, thresholds['score_put_forte']))
        thresholds['score_put'] = min(-2.0, max(-6.0, thresholds['score_put']))
        thresholds['confianca_minima'] = max(0.3, min(0.9, thresholds['confianca_minima']))
        
        print(f"\n🎯 Thresholds Otimizados:")
        for key, value in thresholds.items():
            print(f"  {key}: {value}")
        
        return thresholds
    
    def atualizar_estatisticas(self):
        """Atualiza estatísticas mantendo estrutura original"""
        if not self.metricas_extraidas:
            return self.modelo_atual['estatisticas']
        
        df = pd.DataFrame(self.metricas_extraidas)
        
        total = len(df)
        lucrativas = df[df['lucro_percentual'] > 0]
        
        estatisticas = {
            'total_operacoes': total,
            'acertos': len(lucrativas),
            'erros': total - len(lucrativas),
            'lucro_total': round(df['lucro_percentual'].sum(), 4),
            'historico_scores': [round(s, 4) for s in df['score'].tolist() if s != 0]
        }
        
        # Mantém somente os campos originais
        # Remove campos extras que podem ter sido adicionados
        campos_originais = ['total_operacoes', 'acertos', 'erros', 'lucro_total', 'historico_scores']
        estatisticas_finais = {k: estatisticas[k] for k in campos_originais if k in estatisticas}
        
        print(f"\n📊 Estatísticas Atualizadas:")
        print(f"  Total: {estatisticas_finais['total_operacoes']}")
        print(f"  Acertos: {estatisticas_finais['acertos']}")
        print(f"  Erros: {estatisticas_finais['erros']}")
        print(f"  Lucro Total: {estatisticas_finais['lucro_total']:.2f}%")
        print(f"  Scores no Histórico: {len(estatisticas_finais['historico_scores'])}")
        
        return estatisticas_finais
    
    def salvar_modelo(self, arquivo_saida=None):
        """
        Salva o modelo EXATAMENTE na estrutura original
        """
        if arquivo_saida is None:
            arquivo_saida = self.arquivo_modelo
        
        # Mantém a estrutura exata
        modelo_atualizado = {
            'pesos': self.otimizar_pesos(),
            'thresholds': self.otimizar_thresholds(),
            'estatisticas': self.atualizar_estatisticas(),
            'taxa_aprendizado': self.modelo_atual.get('taxa_aprendizado', 0.01),
            'data_atualizacao': datetime.now().isoformat()
        }
        
        # Remove campos extras que podem ter sido adicionados
        campos_permitidos = ['pesos', 'thresholds', 'estatisticas', 'taxa_aprendizado', 'data_atualizacao']
        modelo_limpo = {k: modelo_atualizado[k] for k in campos_permitidos if k in modelo_atualizado}
        
        # Salva
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(modelo_limpo, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Modelo salvo em: {arquivo_saida}")
        print(f"  Estrutura mantida: {list(modelo_limpo.keys())}")
        
        return modelo_limpo
    
    def treinar_e_atualizar(self):
        """
        Pipeline completo mantendo compatibilidade
        """
        print("=" * 60)
        print("🚀 TREINAMENTO - MANTENDO ESTRUTURA ORIGINAL")
        print("=" * 60)
        
        # 1. Otimiza pesos
        pesos = self.otimizar_pesos()
        
        # 2. Otimiza thresholds
        thresholds = self.otimizar_thresholds()
        
        # 3. Atualiza estatísticas
        estatisticas = self.atualizar_estatisticas()
        
        # 4. Salva
        modelo = self.salvar_modelo()
        
        print("\n✅ Treinamento concluído com sucesso!")
        return modelo
    


    # ===== USO CORRETO =====

# Inicializa com os arquivos
treinador = TreinadorCompativel(
    arquivo_modelo='modelo_opcoes.json',
    arquivo_dados='finalizados.json'
)

# Executa treinamento (mantém estrutura original)
modelo = treinador.treinar_e_atualizar()

# Verifica estrutura
print("\n🔍 Verificando estrutura:")
print(f"Pesos: {list(modelo['pesos'].keys())}")
print(f"Thresholds: {list(modelo['thresholds'].keys())}")
print(f"Estatísticas: {list(modelo['estatisticas'].keys())}")