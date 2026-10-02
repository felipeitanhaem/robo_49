import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import sklearn.exceptions
import joblib
import json
import os
import datetime
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# ==================== PARTE 1: MODELO PYTORCH (LSTM) ====================

class LSTMPredictor(nn.Module):
    """
    Rede Neural LSTM para previsão de séries temporais
    """
    def __init__(self, input_size, hidden_size=64, num_layers=2, output_size=1, dropout=0.2):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        # Inicializar estados ocultos
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        
        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Pegar última saída
        out = out[:, -1, :]
        out = self.dropout(out)
        out = self.fc(out)
        out = self.sigmoid(out)
        
        return out

# ==================== PARTE 2: SISTEMA DE ENSEMBLE ====================

class EnsemblePredictor:
    """
    Sistema de ensemble com scikit-learn e PyTorch
    """
    
    def __init__(self, arquivo_modelo="ensemble_modelo.pkl"):
        self.arquivo_modelo = arquivo_modelo
        
        # Modelos scikit-learn
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        # Modelo PyTorch (inicializado depois)
        self.lstm_model = None
        self.lstm_input_size = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Scaler para normalização
        self.scaler = StandardScaler()
        
        # Pesos do ensemble (aprendidos)
        self.pesos_ensemble = {
            'random_forest': 0.4,
            'gradient_boosting': 0.3,
            'lstm': 0.3
        }
        
        # Histórico de treinamento
        self.historico_treino = {
            'rf_acuracia': [],
            'gb_acuracia': [],
            'lstm_loss': [],
            'ensemble_acuracia': []
        }
        
        # Flag para indicar se o modelo já foi treinado
        self.is_trained = False
        
        # Carregar modelo se existir
        self.carregar_modelo()
    
    # ==================== DADOS SINTÉTICOS ====================
    
    def gerar_dados_sinteticos(self, n_amostras=100):
        """
        Gera dados sintéticos para treinamento inicial
        """
        print(f"🔄 Gerando {n_amostras} amostras sintéticas para treinamento...")
        dados = []
        
        for _ in range(n_amostras):
            # Escolher tendência
            tendencia = np.random.choice(['alta', 'baixa', 'neutra'], p=[0.4, 0.4, 0.2])
            
            # Gerar features baseadas na tendência
            if tendencia == 'alta':
                slope = np.random.uniform(0.1, 0.4)
                velocidade = np.random.uniform(0.1, 0.5)
                aceleracao = np.random.uniform(0.05, 0.2)
                rsi_base = np.random.uniform(55, 75)
                label = 1
            elif tendencia == 'baixa':
                slope = np.random.uniform(-0.4, -0.1)
                velocidade = np.random.uniform(-0.5, -0.1)
                aceleracao = np.random.uniform(-0.2, -0.05)
                rsi_base = np.random.uniform(25, 45)
                label = 0
            else:
                slope = np.random.uniform(-0.05, 0.05)
                velocidade = np.random.uniform(-0.1, 0.1)
                aceleracao = np.random.uniform(-0.05, 0.05)
                rsi_base = np.random.uniform(45, 55)
                label = 1 if np.random.random() > 0.5 else 0
            
            # Gerar MA baseada no RSI
            ma_base = rsi_base + np.random.uniform(-5, 5)
            
            # Criar registro
            registro = {
                'slope': slope,
                'velocidade': velocidade,
                'aceleracao': aceleracao,
                'momento': np.random.uniform(-2, 2),
                'correlacao': np.random.uniform(-0.8, 0.8),
                'cruzamento': np.random.choice([-1, 0, 1]),
                'rsi_atual': rsi_base + np.random.uniform(-3, 3),
                'ma_atual': ma_base + np.random.uniform(-3, 3),
                'diff_atual': np.random.uniform(-15, 15),
                'volatilidade': np.random.uniform(0.1, 3),
                'label': label,
                'rsi_historico': [rsi_base + np.random.uniform(-10, 10) for _ in range(10)],
                'ma_historico': [ma_base + np.random.uniform(-10, 10) for _ in range(10)]
            }
            dados.append(registro)
        
        return dados
    
    # ==================== PREPARAÇÃO DE DADOS ====================
    
    def preparar_dados(self, dados_historicos):
        """
        Prepara os dados para treinamento
        dados_historicos: lista de dicionários com features e labels
        """
        features_list = []
        labels_list = []
        series_temporais = []  # Para LSTM
        
        for registro in dados_historicos:
            # Features para scikit-learn
            features = [
                registro['slope'],
                registro['velocidade'],
                registro['aceleracao'],
                registro['momento'],
                registro['correlacao'],
                registro['cruzamento'],
                registro['rsi_atual'],
                registro['ma_atual'],
                registro['diff_atual'],
                registro['volatilidade']
            ]
            features_list.append(features)
            labels_list.append(registro['label'])  # 1 = lucro, 0 = prejuízo
            
            # Série temporal para LSTM (últimos 10 valores de RSI e MA)
            if 'rsi_historico' in registro and 'ma_historico' in registro:
                serie = np.column_stack([
                    registro['rsi_historico'][-10:],
                    registro['ma_historico'][-10:]
                ])
                series_temporais.append(serie)
        
        X = np.array(features_list)
        y = np.array(labels_list)
        X_series = np.array(series_temporais) if series_temporais else None
        
        return X, y, X_series
    
    # ==================== TREINAMENTO ====================
    
    def treinar(self, dados_historicos, epochs=100, batch_size=32):
        """
        Treina todos os modelos do ensemble
        """
        print("🔄 Preparando dados...")
        X, y, X_series = self.preparar_dados(dados_historicos)
        
        if len(X) < 10:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Normalizar
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # ----- 1. Treinar Random Forest -----
        print("🌲 Treinando Random Forest...")
        self.rf_model.fit(X_train_scaled, y_train)
        rf_pred = self.rf_model.predict(X_test_scaled)
        rf_acuracia = accuracy_score(y_test, rf_pred)
        self.historico_treino['rf_acuracia'].append(rf_acuracia)
        print(f"   ✅ Random Forest Acurácia: {rf_acuracia:.2%}")
        
        # ----- 2. Treinar Gradient Boosting -----
        print("📈 Treinando Gradient Boosting...")
        self.gb_model.fit(X_train_scaled, y_train)
        gb_pred = self.gb_model.predict(X_test_scaled)
        gb_acuracia = accuracy_score(y_test, gb_pred)
        self.historico_treino['gb_acuracia'].append(gb_acuracia)
        print(f"   ✅ Gradient Boosting Acurácia: {gb_acuracia:.2%}")
        
        # ----- 3. Treinar LSTM (se houver dados de série temporal) -----
        lstm_acuracia = 0.5
        if X_series is not None and len(X_series) > 10:
            print("🧠 Treinando LSTM (PyTorch)...")
            lstm_acuracia = self._treinar_lstm(X_series, y, epochs, batch_size)
            self.historico_treino['lstm_loss'].append(lstm_acuracia)
            print(f"   ✅ LSTM Acurácia: {lstm_acuracia:.2%}")
        else:
            print("⚠️ Dados insuficientes para LSTM, usando apenas scikit-learn")
            self.pesos_ensemble['lstm'] = 0
            # Redistribuir pesos
            total = self.pesos_ensemble['random_forest'] + self.pesos_ensemble['gradient_boosting']
            if total > 0:
                self.pesos_ensemble['random_forest'] = self.pesos_ensemble['random_forest'] / total
                self.pesos_ensemble['gradient_boosting'] = self.pesos_ensemble['gradient_boosting'] / total
        
        # ----- 4. Ajustar pesos do ensemble -----
        self._ajustar_pesos_ensemble()
        
        # ----- 5. Marcar como treinado -----
        self.is_trained = True
        
        # ----- 6. Salvar modelo -----
        self.salvar_modelo()
        
        print("\n✅ Treinamento concluído!")
        print(f"📊 Pesos do ensemble: {self.pesos_ensemble}")
        
        return True
    
    def _treinar_lstm(self, X_series, y, epochs, batch_size):
        """
        Treina a LSTM
        """
        # Configurar LSTM
        self.lstm_input_size = X_series.shape[2]  # número de features (RSI + MA)
        
        # Criar modelo
        self.lstm_model = LSTMPredictor(
            input_size=self.lstm_input_size,
            hidden_size=64,
            num_layers=2,
            output_size=1
        ).to(self.device)
        
        # Preparar dados
        X_tensor = torch.FloatTensor(X_series)
        y_tensor = torch.FloatTensor(y).view(-1, 1)
        
        # Dividir dados
        split = int(len(X_tensor) * 0.8)
        X_train, X_test = X_tensor[:split], X_tensor[split:]
        y_train, y_test = y_tensor[:split], y_tensor[split:]
        
        # Criar DataLoader
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Configurar otimizador e loss
        optimizer = optim.Adam(self.lstm_model.parameters(), lr=0.001)
        criterion = nn.BCELoss()
        
        # Treinar
        self.lstm_model.train()
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.lstm_model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                avg_loss = epoch_loss / len(train_loader)
                self.historico_treino['lstm_loss'].append(avg_loss)
        
        # Avaliar
        self.lstm_model.eval()
        with torch.no_grad():
            X_test = X_test.to(self.device)
            predictions = self.lstm_model(X_test)
            predictions = predictions.cpu().numpy()
            predictions = (predictions > 0.5).astype(int)
            
            y_test_np = y_test.numpy()
            acuracia = accuracy_score(y_test_np, predictions)
        
        return acuracia
    
    def _ajustar_pesos_ensemble(self):
        """
        Ajusta os pesos do ensemble baseado no desempenho de cada modelo
        """
        # Calcular acurácias
        rf_acc = self.historico_treino['rf_acuracia'][-1] if self.historico_treino['rf_acuracia'] else 0.5
        gb_acc = self.historico_treino['gb_acuracia'][-1] if self.historico_treino['gb_acuracia'] else 0.5
        lstm_acc = self.historico_treino['lstm_loss'][-1] if self.historico_treino['lstm_loss'] else 0.5
        
        # Normalizar para pesos (soma = 1)
        total = rf_acc + gb_acc + lstm_acc
        if total > 0:
            self.pesos_ensemble['random_forest'] = rf_acc / total
            self.pesos_ensemble['gradient_boosting'] = gb_acc / total
            self.pesos_ensemble['lstm'] = lstm_acc / total
    
    # ==================== PREVISÃO ====================
    
    def prever(self, features, serie_temporal=None):
        """
        Faz previsão usando ensemble
        """
        # Verificar se o modelo está treinado
        if not self.is_trained:
            print("⚠️ Modelo não treinado. Gerando dados sintéticos para treinamento...")
            dados_sinteticos = self.gerar_dados_sinteticos(100)
            self.treinar(dados_sinteticos, epochs=30)
        
        # Normalizar features
        try:
            features_scaled = self.scaler.transform([features])
        except sklearn.exceptions.NotFittedError:
            print("⚠️ Scaler não treinado. Gerando dados sintéticos...")
            dados_sinteticos = self.gerar_dados_sinteticos(100)
            self.treinar(dados_sinteticos, epochs=30)
            features_scaled = self.scaler.transform([features])
        
        # Previsões individuais
        rf_pred = self.rf_model.predict_proba(features_scaled)[0][1]
        gb_pred = self.gb_model.predict_proba(features_scaled)[0][1]
        
        # Previsão da LSTM
        lstm_pred = 0.5  # valor padrão
        if self.lstm_model is not None and serie_temporal is not None:
            try:
                self.lstm_model.eval()
                with torch.no_grad():
                    serie_tensor = torch.FloatTensor(serie_temporal).unsqueeze(0).to(self.device)
                    lstm_pred = self.lstm_model(serie_tensor).cpu().numpy()[0][0]
            except:
                lstm_pred = 0.5
        
        # Combinar previsões
        previsao_ensemble = (
            self.pesos_ensemble['random_forest'] * rf_pred +
            self.pesos_ensemble['gradient_boosting'] * gb_pred +
            self.pesos_ensemble['lstm'] * lstm_pred
        )
        
        return {
            'probabilidade_sucesso': previsao_ensemble,
            'previsoes_individuais': {
                'random_forest': rf_pred,
                'gradient_boosting': gb_pred,
                'lstm': lstm_pred
            },
            'pesos_ensemble': self.pesos_ensemble,
            'decisao': 'COMPRAR' if previsao_ensemble > 0.6 else 'AGUARDAR'
        }
    
    # ==================== PERSISTÊNCIA ====================
    
    def salvar_modelo(self):
        """
        Salva todos os modelos
        """
        modelo = {
            'rf_model': self.rf_model,
            'gb_model': self.gb_model,
            'scaler': self.scaler,
            'pesos_ensemble': self.pesos_ensemble,
            'historico_treino': self.historico_treino,
            'is_trained': self.is_trained
        }
        
        try:
            joblib.dump(modelo, self.arquivo_modelo)
            
            # Salvar LSTM separadamente se existir
            if self.lstm_model is not None:
                torch.save(self.lstm_model.state_dict(), 'lstm_model.pth')
                with open('lstm_config.json', 'w') as f:
                    json.dump({
                        'input_size': self.lstm_input_size
                    }, f)
            
            return True
        except Exception as e:
            print(f"Erro ao salvar modelo: {e}")
            return False
    
    def carregar_modelo(self):
        """
        Carrega modelos salvos
        """
        if not os.path.exists(self.arquivo_modelo):
            print("Nenhum modelo salvo encontrado.")
            return False
        
        try:
            modelo = joblib.load(self.arquivo_modelo)
            self.rf_model = modelo['rf_model']
            self.gb_model = modelo['gb_model']
            self.scaler = modelo['scaler']
            self.pesos_ensemble = modelo['pesos_ensemble']
            self.historico_treino = modelo['historico_treino']
            self.is_trained = modelo.get('is_trained', False)
            
            # Carregar LSTM
            if os.path.exists('lstm_model.pth'):
                with open('lstm_config.json', 'r') as f:
                    config = json.load(f)
                
                self.lstm_input_size = config['input_size']
                self.lstm_model = LSTMPredictor(
                    input_size=self.lstm_input_size,
                    hidden_size=64,
                    num_layers=2,
                    output_size=1
                ).to(self.device)
                self.lstm_model.load_state_dict(torch.load('lstm_model.pth', map_location=self.device))
            
            print(f"✅ Modelo carregado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao carregar modelo: {e}")
            return False

# ==================== PARTE 3: INTEGRAÇÃO COM SEU SISTEMA ====================

class SistemaOpcoesInteligente:
    """
    Sistema completo integrando sua lógica com o ensemble
    """
    
    def __init__(self):
        self.ensemble = EnsemblePredictor()
        self.historico_operacoes = []
        self.ultimo_estado = None
        
    def analisar_opcao(self, opcao, dados_mercado):
        """
        Analisa opção usando o ensemble
        """
        # Calcular métricas (sua lógica existente)
        metricas = self._calcular_metricas(dados_mercado)
        
        # Features para scikit-learn
        features = [
            metricas['slope'],
            metricas['velocidade'],
            metricas['aceleracao'],
            metricas['momento'],
            metricas['correlacao'],
            metricas['cruzamento'],
            metricas['rsi_atual'],
            metricas['ma_atual'],
            metricas['diff_atual'],
            metricas['volatilidade']
        ]
        
        # Série temporal para LSTM
        serie_temporal = None
        if 'rsi_historico' in dados_mercado and 'ma_historico' in dados_mercado:
            rsi_hist = dados_mercado['rsi_historico'][-10:]
            ma_hist = dados_mercado['ma_historico'][-10:]
            if len(rsi_hist) >= 10:
                serie_temporal = np.column_stack([rsi_hist, ma_hist])
        
        # Fazer previsão
        previsao = self.ensemble.prever(features, serie_temporal)
        
        # Combinar com sua lógica de tendência
        sinal_final = self._decidir_sinal(metricas, previsao)
        
        # Guardar estado
        self.ultimo_estado = {
            'timestamp': datetime.datetime.now(),
            'opcao': opcao,
            'metricas': metricas,
            'previsao': previsao,
            'sinal_final': sinal_final,
            'preco_entrada': dados_mercado.get('preco_atual')
        }
        
        return sinal_final
    
    def _calcular_metricas(self, dados):
        """
        Calcula métricas (sua função original adaptada)
        """
        rsi = np.array(dados['rsi_list'][-7:])
        ma = np.array(dados['ma_list'][-7:])
        diff = rsi - ma
        
        x = np.arange(len(diff))
        slope, _ = np.polyfit(x, diff, 1)
        
        correlacao = np.corrcoef(x, diff)[0, 1] if len(diff) > 1 else 0
        velocidade = diff[-1] - diff[-2] if len(diff) >= 2 else 0
        
        if len(diff) >= 3:
            aceleracao = (diff[-1] - diff[-2]) - (diff[-2] - diff[-3])
        else:
            aceleracao = 0
        
        if len(diff) >= 3:
            momento = np.mean(diff[-3:]) - np.mean(diff)
        else:
            momento = 0
        
        cruzamento = 0
        if len(diff) >= 2:
            if diff[-2] < 0 and diff[-1] > 0:
                cruzamento = 1
            elif diff[-2] > 0 and diff[-1] < 0:
                cruzamento = -1
        
        return {
            'slope': slope,
            'correlacao': correlacao,
            'velocidade': velocidade,
            'aceleracao': aceleracao,
            'momento': momento,
            'cruzamento': cruzamento,
            'volatilidade': np.std(diff),
            'rsi_atual': rsi[-1],
            'ma_atual': ma[-1],
            'diff_atual': diff[-1]
        }
    
    def _decidir_sinal(self, metricas, previsao):
        """
        Decide sinal final combinando análise técnica com ML
        """
        # Score técnico (sua lógica existente)
        score_tecnico = self._calcular_score_tecnico(metricas)
        
        # Confiança do ensemble
        prob_sucesso = previsao['probabilidade_sucesso']
        
        # Decisão combinada
        if prob_sucesso > 0.7 and score_tecnico > 3:
            return {
                'sinal': 'CALL_FORTE',
                'confianca': 0.9,
                'motivo': 'alinhamento_forte',
                'prob_ml': prob_sucesso,
                'score_tecnico': score_tecnico
            }
        elif prob_sucesso > 0.6 and score_tecnico > 1.5:
            return {
                'sinal': 'CALL',
                'confianca': 0.7,
                'motivo': 'alinhamento_moderado',
                'prob_ml': prob_sucesso,
                'score_tecnico': score_tecnico
            }
        elif prob_sucesso < 0.3 and score_tecnico < -3:
            return {
                'sinal': 'PUT_FORTE',
                'confianca': 0.9,
                'motivo': 'alinhamento_forte_baixa',
                'prob_ml': prob_sucesso,
                'score_tecnico': score_tecnico
            }
        elif prob_sucesso < 0.4 and score_tecnico < -1.5:
            return {
                'sinal': 'PUT',
                'confianca': 0.7,
                'motivo': 'alinhamento_moderado_baixa',
                'prob_ml': prob_sucesso,
                'score_tecnico': score_tecnico
            }
        else:
            return {
                'sinal': 'NEUTRO',
                'confianca': 0.3,
                'motivo': 'divergencia',
                'prob_ml': prob_sucesso,
                'score_tecnico': score_tecnico
            }
    
    def _calcular_score_tecnico(self, metricas):
        """
        Calcula score técnico (sua lógica existente)
        """
        score = 0
        
        # Tendência
        if metricas['slope'] > 0.15:
            score += 3
        elif metricas['slope'] > 0.05:
            score += 1.5
        elif metricas['slope'] < -0.15:
            score -= 3
        elif metricas['slope'] < -0.05:
            score -= 1.5
        
        # Velocidade
        if metricas['velocidade'] > 0.2:
            score += 2
        elif metricas['velocidade'] > 0.05:
            score += 1
        elif metricas['velocidade'] < -0.2:
            score -= 2
        elif metricas['velocidade'] < -0.05:
            score -= 1
        
        # Aceleração
        if metricas['aceleracao'] > 0.1:
            score += 1
        elif metricas['aceleracao'] < -0.1:
            score -= 1
        
        # Cruzamento
        score += metricas['cruzamento'] * 1
        
        return score
    
    def registrar_resultado(self, lucro_percentual):
        """
        Registra resultado e adiciona ao histórico de treinamento
        """
        if self.ultimo_estado is None:
            return
        
        # Criar registro de treinamento
        registro = {
            'slope': self.ultimo_estado['metricas']['slope'],
            'velocidade': self.ultimo_estado['metricas']['velocidade'],
            'aceleracao': self.ultimo_estado['metricas']['aceleracao'],
            'momento': self.ultimo_estado['metricas']['momento'],
            'correlacao': self.ultimo_estado['metricas']['correlacao'],
            'cruzamento': self.ultimo_estado['metricas']['cruzamento'],
            'rsi_atual': self.ultimo_estado['metricas']['rsi_atual'],
            'ma_atual': self.ultimo_estado['metricas']['ma_atual'],
            'diff_atual': self.ultimo_estado['metricas']['diff_atual'],
            'volatilidade': self.ultimo_estado['metricas']['volatilidade'],
            'label': 1 if lucro_percentual > 0 else 0,
            'lucro': lucro_percentual
        }
        
        self.historico_operacoes.append(registro)
        
        # Se tiver dados suficientes, treinar novamente
        if len(self.historico_operacoes) >= 20 and len(self.historico_operacoes) % 10 == 0:
            print(f"\n🔄 Retreinando modelo com {len(self.historico_operacoes)} operações...")
            self.ensemble.treinar(self.historico_operacoes, epochs=50)
    
    def get_estatisticas(self):
        """
        Retorna estatísticas do sistema
        """
        if len(self.historico_operacoes) == 0:
            return {'total_operacoes': 0}
        
        lucros = [op['lucro'] for op in self.historico_operacoes]
        acertos = sum(1 for op in self.historico_operacoes if op['label'] == 1)
        
        return {
            'total_operacoes': len(self.historico_operacoes),
            'taxa_acerto': acertos / len(self.historico_operacoes) * 100,
            'lucro_medio': np.mean(lucros),
            'lucro_total': np.sum(lucros),
            'maior_lucro': np.max(lucros),
            'maior_prejuizo': np.min(lucros)
        }

# ==================== PARTE 4: EXEMPLO DE USO ====================

def exemplo_uso():
    """
    Exemplo completo de como usar o sistema
    """
    
    # 1. Inicializar sistema
    sistema = SistemaOpcoesInteligente()
    
    # 2. Dados de exemplo (substituir com dados reais do MT5)
    dados_exemplo = {
        'rsi_list': [45, 47, 50, 52, 55, 58, 62],
        'ma_list': [43, 44, 45, 46, 47, 48, 49],
        'rsi_historico': [40, 42, 45, 48, 50, 52, 55, 58, 60, 62],
        'ma_historico': [38, 39, 40, 41, 42, 43, 44, 45, 46, 47],
        'preco_atual': 45.50
    }
    
    # 3. Analisar opção
    print("📊 Analisando opção...")
    resultado = sistema.analisar_opcao("PETR4", dados_exemplo)
    
    print(f"\n🎯 Resultado da análise:")
    print(f"   Sinal: {resultado['sinal']}")
    print(f"   Confiança: {resultado['confianca']:.1%}")
    print(f"   Motivo: {resultado['motivo']}")
    print(f"   Probabilidade ML: {resultado['prob_ml']:.1%}")
    print(f"   Score Técnico: {resultado['score_tecnico']:.2f}")
    
    # 4. Simular resultado
    if resultado['sinal'] in ['CALL', 'CALL_FORTE']:
        # Simular lucro de 5%
        lucro = 5.0
        print(f"\n💰 Operação simulada: +{lucro}%")
        sistema.registrar_resultado(lucro)
    
    # 5. Ver estatísticas
    stats = sistema.get_estatisticas()
    print(f"\n📊 Estatísticas:")
    print(f"   Total operações: {stats['total_operacoes']}")
    print(f"   Taxa de acerto: {stats['taxa_acerto']:.1f}%")
    print(f"   Lucro médio: {stats['lucro_medio']:.2f}%")

if __name__ == "__main__":
    exemplo_uso()