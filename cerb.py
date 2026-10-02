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
#from datetime import datetime
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

# ==================== PARTE 3: INTEGRAÇÃO COM SUA ROTINA ====================

# Instância global do sistema de ML
sistema_ml = None

def inicializar_ml():
    """Inicializa o sistema de machine learning"""
    global sistema_ml
    if sistema_ml is None:
        sistema_ml = EnsemblePredictor()
    return sistema_ml

def calcular_metricas_ml(rsi_list, ma_list):
    """
    Calcula as métricas necessárias para o ML a partir dos dados
    """
    rsi = np.array(rsi_list[-7:])
    ma = np.array(ma_list[-7:])
    diff = rsi - ma
    
    # Normalizar diff
    diff_max = np.max(np.abs(diff))
    if diff_max > 0:
        diff_normalizado = diff / diff_max
    else:
        diff_normalizado = diff
    
    x = np.arange(len(diff_normalizado))
    slope, _ = np.polyfit(x, diff_normalizado, 1)
    correlacao = np.corrcoef(x, diff_normalizado)[0, 1] if len(diff_normalizado) > 1 else 0
    
    # Velocidade
    if len(diff_normalizado) >= 2:
        velocidade = diff_normalizado[-1] - diff_normalizado[-2]
    else:
        velocidade = 0
    
    # Aceleração
    if len(diff_normalizado) >= 3:
        aceleracao = (diff_normalizado[-1] - diff_normalizado[-2]) - (diff_normalizado[-2] - diff_normalizado[-3])
    else:
        aceleracao = 0
    
    # Momento
    if len(diff_normalizado) >= 3:
        media_ultimas_3 = np.mean(diff_normalizado[-3:])
        media_todas = np.mean(diff_normalizado)
        momento = media_ultimas_3 - media_todas
    else:
        momento = 0
    
    # Cruzamento
    cruzamento = 0
    if len(diff_normalizado) >= 2:
        if diff_normalizado[-2] < 0 and diff_normalizado[-1] > 0:
            cruzamento = 1
        elif diff_normalizado[-2] > 0 and diff_normalizado[-1] < 0:
            cruzamento = -1
    
    volatilidade = np.std(diff_normalizado)
    
    return {
        'slope': slope,
        'velocidade': velocidade,
        'aceleracao': aceleracao,
        'momento': momento,
        'correlacao': correlacao,
        'cruzamento': cruzamento,
        'volatilidade': volatilidade,
        'rsi_atual': rsi_list[-1] if rsi_list else 50,
        'ma_atual': ma_list[-1] if ma_list else 50,
        'diff_atual': diff_normalizado[-1] if len(diff_normalizado) > 0 else 0
    }

def sinal_opcoes_30min_melhorado(opcao):
    """
    Versão otimizada para opções 30min com sistema de pesos aprimorado
    E integração com machine learning
    """
    # Importar MT5 (seu código existente)
    #import MetaTrader5 as mt5
    
    symbol = "VALE3"#ativo_principal(opcao)  # Sua função existente
    timeframe = mt5.TIMEFRAME_M30
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)


    
    print ("rates:",len(rates))
    if rates is None or len(rates) < 50:
        return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
    df = pd.DataFrame(rates)
    close_prices = df['close']
    
    # Calcula RSI(5) e EMA(9) sobre o RSI
    rsi_5 = calculate_rsi(close_prices, period=5)  # Sua função existente
    ema_9_rsi = rsi_5.ewm(span=9, adjust=False).mean()
    
    rsi_5 = rsi_5.dropna()
    ema_9_rsi = ema_9_rsi.dropna()
    
    rsi_list = rsi_5.tail(14).tolist()
    ma_list = ema_9_rsi.tail(14).tolist()
    
    if len(rsi_list) < 7:
        return {"sinal": "AGUARDANDO", "confianca": 0, "motivo": "dados_insuficientes"}
    
    # ================== ANÁLISE COM PESOS (SEU CÓDIGO EXISTENTE) ==================
    rsi = np.array(rsi_list[-7:])
    ma = np.array(ma_list[-7:])
    diff = rsi - ma
    
    # ✅ NORMALIZAR O DIFF
    diff_max = np.max(np.abs(diff))
    if diff_max > 0:
        diff_normalizado = diff / diff_max
    else:
        diff_normalizado = diff
    
    # Usar diff_normalizado para os cálculos
    x = np.arange(len(diff_normalizado))
    slope, intercept = np.polyfit(x, diff_normalizado, 1)
    correlacao = np.corrcoef(x, diff_normalizado)[0, 1] if len(diff_normalizado) > 1 else 0
    
    # Velocidade
    if len(diff_normalizado) >= 2:
        velocidade = diff_normalizado[-1] - diff_normalizado[-2]
        velocidade_media = np.mean(np.diff(diff_normalizado)) if len(diff_normalizado) > 2 else velocidade
    else:
        velocidade = 0
        velocidade_media = 0
    
    # Aceleração
    if len(diff_normalizado) >= 3:
        aceleracao = (diff_normalizado[-1] - diff_normalizado[-2]) - (diff_normalizado[-2] - diff_normalizado[-3])
        aceleracao_media = np.mean(np.diff(np.diff(diff_normalizado))) if len(diff_normalizado) > 3 else aceleracao
    else:
        aceleracao = 0
        aceleracao_media = 0
    
    # Momento
    if len(diff_normalizado) >= 3:
        media_ultimas_3 = np.mean(diff_normalizado[-3:])
        media_todas = np.mean(diff_normalizado)
        momento = media_ultimas_3 - media_todas
    else:
        momento = 0
    
    # Cruzamento
    cruzamento = 0
    if len(diff_normalizado) >= 2:
        if diff_normalizado[-2] < 0 and diff_normalizado[-1] > 0:
            cruzamento = 1
        elif diff_normalizado[-2] > 0 and diff_normalizado[-1] < 0:
            cruzamento = -1
    
    # ================== SISTEMA DE PONTUAÇÃO (SEU CÓDIGO EXISTENTE) ==================
    score = 0
    detalhes_score = {}
    
    # 1. TENDÊNCIA (peso 4)
    if slope > 0.3:
        score += 4
        detalhes_score['tendencia'] = 4
    elif slope > 0.15:
        score += 3
        detalhes_score['tendencia'] = 3
    elif slope > 0.05:
        score += 1.5
        detalhes_score['tendencia'] = 1.5
    elif slope < -0.3:
        score -= 4
        detalhes_score['tendencia'] = -4
    elif slope < -0.15:
        score -= 3
        detalhes_score['tendencia'] = -3
    elif slope < -0.05:
        score -= 1.5
        detalhes_score['tendencia'] = -1.5
    else:
        detalhes_score['tendencia'] = 0
    
    # Bônus por correlação forte
    if abs(correlacao) > 0.8:
        score += 1 if slope > 0 else -1
        detalhes_score['correlacao'] = 1 if slope > 0 else -1
    else:
        detalhes_score['correlacao'] = 0
    
    # 2. VELOCIDADE (peso 3)
    if velocidade > 0.3:
        score += 3
        detalhes_score['velocidade'] = 3
    elif velocidade > 0.15:
        score += 2
        detalhes_score['velocidade'] = 2
    elif velocidade > 0.05:
        score += 1
        detalhes_score['velocidade'] = 1
    elif velocidade < -0.3:
        score -= 3
        detalhes_score['velocidade'] = -3
    elif velocidade < -0.15:
        score -= 2
        detalhes_score['velocidade'] = -2
    elif velocidade < -0.05:
        score -= 1
        detalhes_score['velocidade'] = -1
    else:
        detalhes_score['velocidade'] = 0
    
    # 3. ACELERAÇÃO (peso 2)
    if aceleracao > 0.2:
        score += 2
        detalhes_score['aceleracao'] = 2
    elif aceleracao > 0.1:
        score += 1.5
        detalhes_score['aceleracao'] = 1.5
    elif aceleracao > 0.05:
        score += 0.5
        detalhes_score['aceleracao'] = 0.5
    elif aceleracao < -0.2:
        score -= 2
        detalhes_score['aceleracao'] = -2
    elif aceleracao < -0.1:
        score -= 1.5
        detalhes_score['aceleracao'] = -1.5
    elif aceleracao < -0.05:
        score -= 0.5
        detalhes_score['aceleracao'] = -0.5
    else:
        detalhes_score['aceleracao'] = 0
    
    # 4. MOMENTO (peso 1.5)
    if momento > 0.15:
        score += 1.5
        detalhes_score['momento'] = 1.5
    elif momento > 0.05:
        score += 0.75
        detalhes_score['momento'] = 0.75
    elif momento < -0.15:
        score -= 1.5
        detalhes_score['momento'] = -1.5
    elif momento < -0.05:
        score -= 0.75
        detalhes_score['momento'] = -0.75
    else:
        detalhes_score['momento'] = 0
    
    # 5. CRUZAMENTO (peso 1)
    if cruzamento == 1:
        score += 1
        detalhes_score['cruzamento'] = 1
    elif cruzamento == -1:
        score -= 1
        detalhes_score['cruzamento'] = -1
    else:
        detalhes_score['cruzamento'] = 0
    
    # ================== DECISÃO FINAL (SEU CÓDIGO EXISTENTE) ==================
    sinais_positivos = sum(1 for v in detalhes_score.values() if v > 0)
    sinais_negativos = sum(1 for v in detalhes_score.values() if v < 0)
    total_sinais = len([v for v in detalhes_score.values() if v != 0])
    
    if total_sinais > 0:
        consistencia = abs(sinais_positivos - sinais_negativos) / total_sinais
    else:
        consistencia = 0
    
    # Decisão com thresholds ajustados
    if score >= 6 and consistencia > 0.6:
        sinal = "CALL_FORTE"
        confianca = 0.92
        motivo = "tendencia_muito_forte_alta"
    elif score >= 4:
        sinal = "CALL"
        confianca = 0.75 + (score - 4) * 0.05
        motivo = "tendencia_forte_alta"
    elif score >= 2:
        sinal = "CALL"
        confianca = 0.60
        motivo = "tendencia_moderada_alta"
    elif score >= 0.5:
        sinal = "LEVE_CALL"
        confianca = 0.50
        motivo = "leve_tendencia_alta"
    elif score <= -6 and consistencia > 0.6:
        sinal = "PUT_FORTE"
        confianca = 0.92
        motivo = "tendencia_muito_forte_baixa"
    elif score <= -4:
        sinal = "PUT"
        confianca = 0.75 + abs(score + 4) * 0.05
        motivo = "tendencia_forte_baixa"
    elif score <= -2:
        sinal = "PUT"
        confianca = 0.60
        motivo = "tendencia_moderada_baixa"
    elif score <= -0.5:
        sinal = "LEVE_PUT"
        confianca = 0.50
        motivo = "leve_tendencia_baixa"
    else:
        sinal = "NEUTRO"
        confianca = 0.30
        motivo = "sem_tendencia_clara"
    
    confianca = min(0.98, confianca)
    
    # ================== INTEGRAÇÃO COM MACHINE LEARNING ==================
    # Inicializar ML
    ml = inicializar_ml()
    
    # Preparar dados para ML
    metricas_ml = calcular_metricas_ml(rsi_list, ma_list)
    
    # Features para o ML
    features_ml = [
        metricas_ml['slope'],
        metricas_ml['velocidade'],
        metricas_ml['aceleracao'],
        metricas_ml['momento'],
        metricas_ml['correlacao'],
        metricas_ml['cruzamento'],
        metricas_ml['rsi_atual'],
        metricas_ml['ma_atual'],
        metricas_ml['diff_atual'],
        metricas_ml['volatilidade']
    ]
    
    # Série temporal para LSTM
    serie_temporal = None
    if len(rsi_list) >= 10 and len(ma_list) >= 10:
        rsi_hist = np.array(rsi_list[-10:])
        ma_hist = np.array(ma_list[-10:])
        serie_temporal = np.column_stack([rsi_hist, ma_hist])
    
    # Fazer previsão com ML
    try:
        previsao_ml = ml.prever(features_ml, serie_temporal)
        prob_ml = previsao_ml['probabilidade_sucesso']
        decisao_ml = previsao_ml['decisao']
    except Exception as e:
        print(f"Erro na previsão ML: {e}")
        prob_ml = 0.5
        decisao_ml = "AGUARDAR"
    
    # ================== COMBINAR DECISÕES ==================
    # Ajustar confiança baseada no ML
    if sinal in ['CALL', 'CALL_FORTE', 'LEVE_CALL']:
        if prob_ml > 0.7:
            confianca = min(0.98, confianca + 0.15)
            motivo = f"{motivo}_ml_confirmado"
        elif prob_ml > 0.6:
            confianca = min(0.95, confianca + 0.08)
            motivo = f"{motivo}_ml_neutro"
        elif prob_ml < 0.4:
            confianca = max(0.3, confianca - 0.15)
            motivo = f"{motivo}_ml_divergente"
    elif sinal in ['PUT', 'PUT_FORTE', 'LEVE_PUT']:
        if prob_ml < 0.3:
            confianca = min(0.98, confianca + 0.15)
            motivo = f"{motivo}_ml_confirmado"
        elif prob_ml < 0.4:
            confianca = min(0.95, confianca + 0.08)
            motivo = f"{motivo}_ml_neutro"
        elif prob_ml > 0.6:
            confianca = max(0.3, confianca - 0.15)
            motivo = f"{motivo}_ml_divergente"
    
    # Decisão final combinada
    decisao_final = decisao_ml if prob_ml > 0.65 else sinal
    
    # ================== RETORNAR RESULTADO ==================
    return {
        'decisao': decisao_final,
        'sinal': sinal,
        'confianca': round(confianca, 2),
        'score': round(score, 2),
        'motivo': motivo,
        'detalhes_score': detalhes_score,
        'slope': round(slope, 4),
        'correlacao': round(correlacao, 3),
        'velocidade': round(velocidade, 4),
        'aceleracao': round(aceleracao, 4),
        'momento': round(momento, 4),
        'cruzamento': cruzamento,
        'diff_atual': round(diff_normalizado[-1], 4),
        'diff_anterior': round(diff_normalizado[-2], 4) if len(diff_normalizado) >= 2 else None,
        'velas_analisadas': len(diff_normalizado),
        'ml_probabilidade': round(prob_ml, 4),
        'ml_decisao': decisao_ml,
        'pesos_ensemble': ml.pesos_ensemble if ml.is_trained else None,
        'previsoes_individuais': previsao_ml.get('previsoes_individuais', {}) if 'previsao_ml' in locals() else {}
    }


# def calculate_rsi(close_prices, period=5):
#     """Calcula RSI"""
#     delta = close_prices.diff()
#     gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
#     loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
#     rs = gain / loss
#     rsi = 100 - (100 / (1 + rs))
#     return rsi

# # ==================== EXEMPLO DE USO ====================

# if __name__ == "__main__":
#     # Inicializar ML
#     inicializar_ml()
    
#     # Exemplo de uso (você precisa ter o MT5 conectado)
#     try:
#         resultado = sinal_opcoes_30min_melhorado("VALES78")
#         print("Resultado:", resultado)
#     except Exception as e:
#         print(f"Erro: {e}")
#         print("Execute este código com o MT5 conectado e dados disponíveis")