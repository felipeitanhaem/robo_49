import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import sklearn.exceptions
import joblib
import json
import os
import datetime
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# ==================== PARTE 1: MODELO PYTORCH (LSTM MELHORADO) ====================

class LSTMPredictor(nn.Module):
    """
    Rede Neural LSTM melhorada com atenção e mais camadas
    """
    def __init__(self, input_size, hidden_size=128, num_layers=3, output_size=1, dropout=0.3):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM com mais camadas
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout, bidirectional=True)
        
        # Camadas adicionais
        self.dropout = nn.Dropout(dropout)
        self.batch_norm = nn.BatchNorm1d(hidden_size * 2)
        
        # Camadas fully connected
        self.fc1 = nn.Linear(hidden_size * 2, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, output_size)
        
        self.sigmoid = nn.Sigmoid()
        self.relu = nn.ReLU()
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers * 2, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers * 2, x.size(0), self.hidden_size)
        
        out, _ = self.lstm(x, (h0, c0))
        out = out[:, -1, :]
        out = self.dropout(out)
        out = self.batch_norm(out)
        
        out = self.fc1(out)
        out = self.relu(out)
        out = self.dropout(out)
        
        out = self.fc2(out)
        out = self.relu(out)
        out = self.dropout(out)
        
        out = self.fc3(out)
        out = self.sigmoid(out)
        
        return out

# ==================== PARTE 2: SISTEMA DE ENSEMBLE MELHORADO ====================

class EnsemblePredictor:
    """
    Sistema de ensemble melhorado com mais modelos e features
    """
    
    def __init__(self, arquivo_modelo="ensemble_modelo_v2.pkl"):
        self.arquivo_modelo = arquivo_modelo
        
        # Modelos scikit-learn melhorados
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=3,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1
        )
        
        self.gb_model = GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=6,
            min_samples_split=3,
            min_samples_leaf=2,
            subsample=0.8,
            random_state=42
        )
        
        # Adicionar XGBoost se disponível
        self.xgb_model = None
        try:
            from xgboost import XGBClassifier
            self.xgb_model = XGBClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            print("✅ XGBoost disponível")
        except ImportError:
            print("⚠️ XGBoost não disponível, usando apenas RF e GB")
        
        # Modelo PyTorch
        self.lstm_model = None
        self.lstm_input_size = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"📱 Dispositivo: {self.device}")
        
        # Scaler
        self.scaler = StandardScaler()
        
        # Pesos do ensemble
        self.pesos_ensemble = {
            'random_forest': 0.35,
            'gradient_boosting': 0.30,
            'xgboost': 0.20,
            'lstm': 0.15
        }
        
        # Histórico de treinamento
        self.historico_treino = {
            'rf_acuracia': [],
            'gb_acuracia': [],
            'xgb_acuracia': [],
            'lstm_acuracia': [],
            'ensemble_acuracia': [],
            'ensemble_f1': []
        }
        
        self.is_trained = False
        self.carregar_modelo()
    
    # ==================== DADOS SINTÉTICOS ====================
    
    def gerar_dados_sinteticos(self, n_amostras=500):
        """Gera dados sintéticos realistas para treinamento"""
        print(f"🔄 Gerando {n_amostras} amostras sintéticas...")
        dados = []
        
        for _ in range(n_amostras):
            tendencia = np.random.choice(['alta', 'baixa', 'neutra'], p=[0.35, 0.35, 0.3])
            volatilidade_base = np.random.uniform(0.5, 3.0)
            ruido = np.random.normal(0, 0.1)
            
            if tendencia == 'alta':
                slope = np.random.uniform(0.05, 0.5) + ruido * 0.1
                velocidade = np.random.uniform(0.05, 0.5) + ruido * 0.05
                aceleracao = np.random.uniform(0.02, 0.2) + ruido * 0.02
                rsi_base = np.random.uniform(55, 80)
                label = 1
            elif tendencia == 'baixa':
                slope = np.random.uniform(-0.5, -0.05) + ruido * 0.1
                velocidade = np.random.uniform(-0.5, -0.05) + ruido * 0.05
                aceleracao = np.random.uniform(-0.2, -0.02) + ruido * 0.02
                rsi_base = np.random.uniform(20, 45)
                label = 0
            else:
                slope = np.random.uniform(-0.05, 0.05) + ruido * 0.05
                velocidade = np.random.uniform(-0.1, 0.1) + ruido * 0.05
                aceleracao = np.random.uniform(-0.05, 0.05) + ruido * 0.02
                rsi_base = np.random.uniform(45, 55)
                label = 1 if np.random.random() > 0.5 else 0
            
            ma_base = rsi_base + np.random.uniform(-8, 8)
            
            # Criar histórico
            rsi_hist = [rsi_base]
            ma_hist = [ma_base]
            for i in range(1, 30):
                if tendencia == 'alta':
                    passo_rsi = np.random.uniform(0.1, 1.5) + ruido * 0.2
                    passo_ma = np.random.uniform(0.05, 0.8) + ruido * 0.1
                elif tendencia == 'baixa':
                    passo_rsi = np.random.uniform(-1.5, -0.1) + ruido * 0.2
                    passo_ma = np.random.uniform(-0.8, -0.05) + ruido * 0.1
                else:
                    passo_rsi = np.random.uniform(-0.5, 0.5) + ruido * 0.3
                    passo_ma = np.random.uniform(-0.3, 0.3) + ruido * 0.2
                
                rsi_hist.append(rsi_hist[-1] + passo_rsi + np.random.uniform(-0.5, 0.5))
                ma_hist.append(ma_hist[-1] + passo_ma + np.random.uniform(-0.3, 0.3))
                rsi_hist[-1] = max(10, min(90, rsi_hist[-1]))
                ma_hist[-1] = max(5, min(95, ma_hist[-1]))
            
            diff_hist = np.array(rsi_hist) - np.array(ma_hist)
            volatilidade = np.std(diff_hist[-20:]) if len(diff_hist) >= 20 else volatilidade_base
            correlacao = np.corrcoef(rsi_hist[-20:], ma_hist[-20:])[0, 1] if len(rsi_hist) >= 20 else np.random.uniform(-0.6, 0.6)
            momento = np.mean(diff_hist[-5:]) - np.mean(diff_hist) if len(diff_hist) >= 5 else 0
            
            cruzamento = 0
            if len(diff_hist) >= 3:
                if diff_hist[-3] < 0 and diff_hist[-1] > 0:
                    cruzamento = 1
                elif diff_hist[-3] > 0 and diff_hist[-1] < 0:
                    cruzamento = -1
            
            forca_tendencia = abs(slope) * (1 + abs(correlacao))
            aceleracao_momento = (diff_hist[-1] - diff_hist[-3]) - (diff_hist[-2] - diff_hist[-4]) if len(diff_hist) >= 4 else 0
            
            registro = {
                'slope': slope,
                'velocidade': velocidade,
                'aceleracao': aceleracao,
                'momento': momento,
                'correlacao': correlacao,
                'cruzamento': cruzamento,
                'rsi_atual': rsi_hist[-1],
                'ma_atual': ma_hist[-1],
                'diff_atual': diff_hist[-1],
                'volatilidade': volatilidade,
                'forca_tendencia': forca_tendencia,
                'aceleracao_momento': aceleracao_momento,
                'rsi_ma_ratio': rsi_hist[-1] / (ma_hist[-1] + 0.001),
                'diff_anterior': diff_hist[-2] if len(diff_hist) >= 2 else diff_hist[-1],
                'rsi_anterior': rsi_hist[-2] if len(rsi_hist) >= 2 else rsi_hist[-1],
                'ma_anterior': ma_hist[-2] if len(ma_hist) >= 2 else ma_hist[-1],
                'probabilidade_estimada': 0.5,
                'label': label,
                'rsi_historico': rsi_hist[-25:],
                'ma_historico': ma_hist[-25:],
                'diff_historico': diff_hist[-25:].tolist()
            }
            dados.append(registro)
        
        return dados
    
    # ==================== PREPARAÇÃO DE DADOS ====================
    
    def preparar_dados(self, dados_historicos):
        """Prepara os dados com 17 features"""
        features_list = []
        labels_list = []
        series_temporais = []
        
        for registro in dados_historicos:
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
                registro['volatilidade'],
                registro.get('forca_tendencia', 0),
                registro.get('aceleracao_momento', 0),
                registro.get('rsi_ma_ratio', 0),
                registro.get('diff_anterior', 0),
                registro.get('rsi_anterior', 0),
                registro.get('ma_anterior', 0),
                registro.get('probabilidade_estimada', 0.5)
            ]
            features_list.append(features)
            labels_list.append(registro['label'])
            
            if 'rsi_historico' in registro and 'ma_historico' in registro:
                rsi_hist = registro['rsi_historico'][-20:]
                ma_hist = registro['ma_historico'][-20:]
                if len(rsi_hist) >= 20:
                    diff_hist = np.array(rsi_hist) - np.array(ma_hist)
                    serie = np.column_stack([
                        rsi_hist,
                        ma_hist,
                        diff_hist,
                        np.gradient(rsi_hist),
                        np.gradient(ma_hist),
                        np.gradient(diff_hist)
                    ])
                    series_temporais.append(serie)
        
        X = np.array(features_list)
        y = np.array(labels_list)
        X_series = np.array(series_temporais) if series_temporais else None
        
        return X, y, X_series
    
    # ==================== TREINAMENTO ====================
    
    def treinar(self, dados_historicos, epochs=100, batch_size=32):
        """Treina todos os modelos do ensemble"""
        print("🔄 Preparando dados...")
        X, y, X_series = self.preparar_dados(dados_historicos)
        
        if len(X) < 20:
            print("❌ Dados insuficientes (mínimo 20 amostras)")
            return False
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Random Forest
        print("🌲 Treinando Random Forest...")
        self.rf_model.fit(X_train_scaled, y_train)
        rf_pred = self.rf_model.predict(X_test_scaled)
        rf_acuracia = accuracy_score(y_test, rf_pred)
        rf_f1 = f1_score(y_test, rf_pred)
        self.historico_treino['rf_acuracia'].append(rf_acuracia)
        print(f"   ✅ RF - Acc: {rf_acuracia:.2%}, F1: {rf_f1:.2%}")
        
        # Gradient Boosting
        print("📈 Treinando Gradient Boosting...")
        self.gb_model.fit(X_train_scaled, y_train)
        gb_pred = self.gb_model.predict(X_test_scaled)
        gb_acuracia = accuracy_score(y_test, gb_pred)
        gb_f1 = f1_score(y_test, gb_pred)
        self.historico_treino['gb_acuracia'].append(gb_acuracia)
        print(f"   ✅ GB - Acc: {gb_acuracia:.2%}, F1: {gb_f1:.2%}")
        
        # XGBoost
        xgb_acuracia = 0.5
        if self.xgb_model is not None:
            print("⚡ Treinando XGBoost...")
            self.xgb_model.fit(X_train_scaled, y_train)
            xgb_pred = self.xgb_model.predict(X_test_scaled)
            xgb_acuracia = accuracy_score(y_test, xgb_pred)
            xgb_f1 = f1_score(y_test, xgb_pred)
            self.historico_treino['xgb_acuracia'].append(xgb_acuracia)
            print(f"   ✅ XGB - Acc: {xgb_acuracia:.2%}, F1: {xgb_f1:.2%}")
        
        # LSTM
        lstm_acuracia = 0.5
        if X_series is not None and len(X_series) > 20:
            print("🧠 Treinando LSTM...")
            lstm_acuracia = self._treinar_lstm(X_series, y, epochs, batch_size)
            self.historico_treino['lstm_acuracia'].append(lstm_acuracia)
            print(f"   ✅ LSTM - Acc: {lstm_acuracia:.2%}")
        
        self._ajustar_pesos_ensemble()
        self.is_trained = True
        self.salvar_modelo()
        
        print(f"\n✅ Treinamento concluído! Pesos: {self.pesos_ensemble}")
        return True
    
    def _treinar_lstm(self, X_series, y, epochs, batch_size):
        """Treina a LSTM com early stopping"""
        self.lstm_input_size = X_series.shape[2]
        
        self.lstm_model = LSTMPredictor(
            input_size=self.lstm_input_size,
            hidden_size=128,
            num_layers=3,
            output_size=1,
            dropout=0.3
        ).to(self.device)
        
        X_tensor = torch.FloatTensor(X_series)
        y_tensor = torch.FloatTensor(y).view(-1, 1)
        
        indices = np.arange(len(X_tensor))
        train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42, stratify=y)
        
        X_train = X_tensor[train_idx]
        y_train = y_tensor[train_idx]
        X_test = X_tensor[test_idx]
        y_test = y_tensor[test_idx]
        
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        optimizer = optim.Adam(self.lstm_model.parameters(), lr=0.0005, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
        criterion = nn.BCELoss()
        
        best_loss = float('inf')
        patience_counter = 0
        
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
                torch.nn.utils.clip_grad_norm_(self.lstm_model.parameters(), 1.0)
                optimizer.step()
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(train_loader)
            scheduler.step(avg_loss)
            
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter > 20:
                    break
        
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
        """Ajusta pesos baseado no desempenho"""
        rf_acc = self.historico_treino['rf_acuracia'][-1] if self.historico_treino['rf_acuracia'] else 0.5
        gb_acc = self.historico_treino['gb_acuracia'][-1] if self.historico_treino['gb_acuracia'] else 0.5
        xgb_acc = self.historico_treino.get('xgb_acuracia', [0.5])[-1] if self.historico_treino.get('xgb_acuracia') else 0.5
        lstm_acc = self.historico_treino.get('lstm_acuracia', [0.5])[-1] if self.historico_treino.get('lstm_acuracia') else 0.5
        
        pesos = []
        modelos = []
        
        if rf_acc > 0.5:
            pesos.append(rf_acc)
            modelos.append('random_forest')
        if gb_acc > 0.5:
            pesos.append(gb_acc)
            modelos.append('gradient_boosting')
        if xgb_acc > 0.5 and self.xgb_model is not None:
            pesos.append(xgb_acc)
            modelos.append('xgboost')
        if lstm_acc > 0.5:
            pesos.append(lstm_acc)
            modelos.append('lstm')
        
        total = sum(pesos)
        if total > 0:
            for i, modelo in enumerate(modelos):
                self.pesos_ensemble[modelo] = pesos[i] / total
            for modelo in ['random_forest', 'gradient_boosting', 'xgboost', 'lstm']:
                if modelo not in self.pesos_ensemble:
                    self.pesos_ensemble[modelo] = 0
    
    # ==================== PREVISÃO ====================
    
    def prever(self, features, serie_temporal=None):
        """Faz previsão usando ensemble"""
        if not self.is_trained:
            print("⚠️ Modelo não treinado. Gerando dados sintéticos...")
            dados_sinteticos = self.gerar_dados_sinteticos(200)
            self.treinar(dados_sinteticos, epochs=50)
        
        if len(features) < 17:
            features = list(features) + [0] * (17 - len(features))
        
        try:
            features_scaled = self.scaler.transform([features])
        except sklearn.exceptions.NotFittedError:
            dados_sinteticos = self.gerar_dados_sinteticos(200)
            self.treinar(dados_sinteticos, epochs=50)
            features_scaled = self.scaler.transform([features])
        
        rf_pred = self.rf_model.predict_proba(features_scaled)[0][1]
        gb_pred = self.gb_model.predict_proba(features_scaled)[0][1]
        
        xgb_pred = 0.5
        if self.xgb_model is not None:
            xgb_pred = self.xgb_model.predict_proba(features_scaled)[0][1]
        
        lstm_pred = 0.5
        if self.lstm_model is not None and serie_temporal is not None:
            try:
                if len(serie_temporal) < 20:
                    pad = np.zeros((20 - len(serie_temporal), serie_temporal.shape[1]))
                    serie_temporal = np.vstack([pad, serie_temporal])
                
                self.lstm_model.eval()
                with torch.no_grad():
                    serie_tensor = torch.FloatTensor(serie_temporal).unsqueeze(0).to(self.device)
                    lstm_pred = self.lstm_model(serie_tensor).cpu().numpy()[0][0]
            except:
                lstm_pred = 0.5
        
        previsao_ensemble = (
            self.pesos_ensemble['random_forest'] * rf_pred +
            self.pesos_ensemble['gradient_boosting'] * gb_pred +
            self.pesos_ensemble.get('xgboost', 0) * xgb_pred +
            self.pesos_ensemble['lstm'] * lstm_pred
        )
        
        preds = [rf_pred, gb_pred, xgb_pred, lstm_pred]
        pesos = [self.pesos_ensemble['random_forest'], 
                 self.pesos_ensemble['gradient_boosting'],
                 self.pesos_ensemble.get('xgboost', 0),
                 self.pesos_ensemble['lstm']]
        
        media_ponderada = previsao_ensemble
        variancia = sum(p * (p_pred - media_ponderada)**2 for p, p_pred in zip(pesos, preds) if p > 0)
        confianca = max(0.3, min(0.98, 1 - variancia * 2))
        
        return {
            'probabilidade_sucesso': previsao_ensemble,
            'confianca': confianca,
            'previsoes_individuais': {
                'random_forest': rf_pred,
                'gradient_boosting': gb_pred,
                'xgboost': xgb_pred,
                'lstm': lstm_pred
            },
            'pesos_ensemble': self.pesos_ensemble,
            'decisao': 'COMPRAR' if previsao_ensemble > 0.6 else 'AGUARDAR'
        }
    
    # ==================== PERSISTÊNCIA ====================
    
    def salvar_modelo(self):
        """Salva todos os modelos"""
        modelo = {
            'rf_model': self.rf_model,
            'gb_model': self.gb_model,
            'xgb_model': self.xgb_model,
            'scaler': self.scaler,
            'pesos_ensemble': self.pesos_ensemble,
            'historico_treino': self.historico_treino,
            'is_trained': self.is_trained,
            'n_features': 17
        }
        
        try:
            joblib.dump(modelo, self.arquivo_modelo)
            if self.lstm_model is not None:
                torch.save(self.lstm_model.state_dict(), 'lstm_model_v2.pth')
                with open('lstm_config_v2.json', 'w') as f:
                    json.dump({'input_size': self.lstm_input_size, 'n_features': 17}, f)
            return True
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            return False
    
    def carregar_modelo(self):
        """Carrega modelos salvos"""
        if not os.path.exists(self.arquivo_modelo):
            print("Nenhum modelo salvo encontrado.")
            return False
        
        try:
            modelo = joblib.load(self.arquivo_modelo)
            self.rf_model = modelo['rf_model']
            self.gb_model = modelo['gb_model']
            self.xgb_model = modelo.get('xgb_model', None)
            self.scaler = modelo['scaler']
            self.pesos_ensemble = modelo['pesos_ensemble']
            self.historico_treino = modelo['historico_treino']
            self.is_trained = modelo.get('is_trained', False)
            
            if os.path.exists('lstm_model_v2.pth'):
                with open('lstm_config_v2.json', 'r') as f:
                    config = json.load(f)
                self.lstm_input_size = config['input_size']
                self.lstm_model = LSTMPredictor(
                    input_size=self.lstm_input_size,
                    hidden_size=128,
                    num_layers=3,
                    output_size=1,
                    dropout=0.3
                ).to(self.device)
                self.lstm_model.load_state_dict(torch.load('lstm_model_v2.pth', map_location=self.device))
            
            print(f"✅ Modelo carregado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao carregar: {e}")
            return False

# ==================== PARTE 3: SISTEMA DE INTEGRAÇÃO ====================

class SistemaOpcoesInteligente:
    """
    Sistema completo integrando análise técnica com IA
    """
    
    def __init__(self):
        self.ensemble = EnsemblePredictor()
        self.historico_operacoes = []
        self.ultimo_estado = None
        self.historico_metricas = deque(maxlen=100)
        
        # TENTAR MIGRAR MODELO ANTIGO
        self._migrar_modelo_antigo()
    
    # ==================== MIGRAÇÃO DO MODELO ANTIGO ====================
    
    def _migrar_modelo_antigo(self, arquivo_json="modelo_opcoes.json"):
        """Migra automaticamente o modelo antigo se existir"""
        if not os.path.exists(arquivo_json):
            return
        
        try:
            print("🔄 Modelo antigo encontrado. Migrando...")
            with open(arquivo_json, 'r') as f:
                modelo_antigo = json.load(f)
            
            # Migrar pesos
            if 'pesos' in modelo_antigo:
                pesos_antigos = modelo_antigo['pesos']
                if isinstance(pesos_antigos, dict):
                    self.ensemble.pesos_ensemble = pesos_antigos
                elif isinstance(pesos_antigos, list) and len(pesos_antigos) >= 3:
                    self.ensemble.pesos_ensemble = {
                        'random_forest': pesos_antigos[0],
                        'gradient_boosting': pesos_antigos[1],
                        'lstm': pesos_antigos[2],
                        'xgboost': 0.0
                    }
                    total = sum(self.ensemble.pesos_ensemble.values())
                    if total > 0:
                        for key in self.ensemble.pesos_ensemble:
                            self.ensemble.pesos_ensemble[key] /= total
            
            # Migrar histórico
            if 'historico' in modelo_antigo:
                for registro in modelo_antigo['historico']:
                    if isinstance(registro, dict):
                        registro_novo = {
                            'slope': registro.get('slope', 0),
                            'velocidade': registro.get('velocidade', 0),
                            'aceleracao': registro.get('aceleracao', 0),
                            'momento': registro.get('momento', 0),
                            'correlacao': registro.get('correlacao', 0),
                            'cruzamento': registro.get('cruzamento', 0),
                            'rsi_atual': registro.get('rsi_atual', 50),
                            'ma_atual': registro.get('ma_atual', 50),
                            'diff_atual': registro.get('diff_atual', 0),
                            'volatilidade': registro.get('volatilidade', 1),
                            'label': registro.get('label', 0),
                            'lucro': registro.get('lucro', 0),
                            'forca_tendencia': abs(registro.get('slope', 0)),
                            'aceleracao_momento': 0,
                            'rsi_ma_ratio': 1,
                            'diff_anterior': 0,
                            'rsi_anterior': 50,
                            'ma_anterior': 50,
                            'probabilidade_estimada': 0.5
                        }
                        self.historico_operacoes.append(registro_novo)
            
            # Migrar métricas
            if 'metricas' in modelo_antigo:
                metricas = modelo_antigo['metricas']
                if 'rf_acuracia' in metricas:
                    self.ensemble.historico_treino['rf_acuracia'] = metricas['rf_acuracia']
                if 'gb_acuracia' in metricas:
                    self.ensemble.historico_treino['gb_acuracia'] = metricas['gb_acuracia']
                if 'lstm_loss' in metricas:
                    self.ensemble.historico_treino['lstm_acuracia'] = metricas['lstm_loss']
            
            # Salvar modelo migrado
            self.ensemble.salvar_modelo()
            
            # Renomear arquivo antigo para backup
            if os.path.exists(arquivo_json):
                backup_name = f"{arquivo_json}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(arquivo_json, backup_name)
                print(f"✅ Modelo antigo migrado e salvo como backup: {backup_name}")
            
            print(f"✅ Migração concluída! {len(self.historico_operacoes)} registros migrados.")
            
            # Se tiver histórico, treinar o modelo
            if len(self.historico_operacoes) >= 30:
                print("🔄 Treinando modelo com dados migrados...")
                self.ensemble.treinar(self.historico_operacoes, epochs=50)
            
        except Exception as e:
            print(f"⚠️ Erro na migração: {e}")
    
    # ==================== MÉTODO DE COMPATIBILIDADE ====================
    
    def analisar(self, opcao, dados_mercado):
        """
        MÉTODO DE COMPATIBILIDADE para código que espera .analisar()
        Retorna no formato que seu código espera (com 'decisao')
        """
        resultado = self.analisar_opcao(opcao, dados_mercado)
        
        estado = {
            'decisao': resultado.get('sinal', 'NEUTRO'),
            'sinal': resultado.get('sinal', 'NEUTRO'),
            'confianca': resultado.get('confianca', 0.5),
            'motivo': resultado.get('motivo', 'sem_informacao'),
            'prob_ml': resultado.get('prob_ml', 0.5),
            'confianca_ml': resultado.get('confianca_ml', 0.5),
            'score_tecnico': resultado.get('score_tecnico', 0),
            'metricas': self.ultimo_estado.get('metricas', {}) if self.ultimo_estado else {},
            'previsao': self.ultimo_estado.get('previsao', {}) if self.ultimo_estado else {}
        }
        
        return estado
    
    # ==================== ANÁLISE ====================
    
    def analisar_opcao(self, opcao, dados_mercado):
        """Analisa opção usando ensemble"""
        metricas = self._calcular_metricas(dados_mercado)
        
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
            metricas['volatilidade'],
            metricas.get('forca_tendencia', 0),
            metricas.get('aceleracao_momento', 0),
            metricas.get('rsi_ma_ratio', 0),
            metricas.get('diff_anterior', 0),
            metricas.get('rsi_anterior', 0),
            metricas.get('ma_anterior', 0),
            metricas.get('probabilidade_estimada', 0.5)
        ]
        
        serie_temporal = None
        if 'rsi_historico' in dados_mercado and 'ma_historico' in dados_mercado:
            rsi_hist = np.array(dados_mercado['rsi_historico'][-25:])
            ma_hist = np.array(dados_mercado['ma_historico'][-25:])
            if len(rsi_hist) >= 20:
                diff_hist = rsi_hist - ma_hist
                serie_temporal = np.column_stack([
                    rsi_hist,
                    ma_hist,
                    diff_hist,
                    np.gradient(rsi_hist),
                    np.gradient(ma_hist),
                    np.gradient(diff_hist)
                ])
        
        previsao = self.ensemble.prever(features, serie_temporal)
        sinal_final = self._decidir_sinal(metricas, previsao)
        
        self.ultimo_estado = {
            'timestamp': datetime.datetime.now(),
            'opcao': opcao,
            'metricas': metricas,
            'previsao': previsao,
            'sinal_final': sinal_final,
            'preco_entrada': dados_mercado.get('preco_atual'),
            'features': features,
            'serie_temporal': serie_temporal
        }
        
        self.historico_metricas.append(metricas)
        
        return sinal_final
    
    def _calcular_metricas(self, dados):
        """Calcula métricas expandidas"""
        rsi = np.array(dados['rsi_list'][-7:])
        ma = np.array(dados['ma_list'][-7:])
        diff = rsi - ma
        
        x = np.arange(len(diff))
        slope, _ = np.polyfit(x, diff, 1)
        correlacao = np.corrcoef(x, diff)[0, 1] if len(diff) > 1 else 0
        
        velocidade = diff[-1] - diff[-2] if len(diff) >= 2 else 0
        aceleracao = (diff[-1] - diff[-2]) - (diff[-2] - diff[-3]) if len(diff) >= 3 else 0
        momento = np.mean(diff[-3:]) - np.mean(diff) if len(diff) >= 3 else 0
        
        cruzamento = 0
        if len(diff) >= 2:
            if diff[-2] < 0 and diff[-1] > 0:
                cruzamento = 1
            elif diff[-2] > 0 and diff[-1] < 0:
                cruzamento = -1
        
        volatilidade = np.std(diff) if len(diff) > 1 else 0.1
        
        forca_tendencia = abs(slope) * (1 + abs(correlacao))
        rsi_ma_ratio = rsi[-1] / (ma[-1] + 0.001)
        
        diff_anterior = diff[-2] if len(diff) >= 2 else diff[-1]
        rsi_anterior = rsi[-2] if len(rsi) >= 2 else rsi[-1]
        ma_anterior = ma[-2] if len(ma) >= 2 else ma[-1]
        
        aceleracao_momento = (diff[-1] - diff[-3]) - (diff[-2] - diff[-4]) if len(diff) >= 4 else 0
        
        prob_estimada = 0.5
        if slope > 0.15 and velocidade > 0.1 and correlacao > 0.5:
            prob_estimada = 0.7
        elif slope < -0.15 and velocidade < -0.1 and correlacao < -0.5:
            prob_estimada = 0.3
        
        return {
            'slope': slope,
            'correlacao': correlacao,
            'velocidade': velocidade,
            'aceleracao': aceleracao,
            'momento': momento,
            'cruzamento': cruzamento,
            'volatilidade': volatilidade,
            'rsi_atual': rsi[-1],
            'ma_atual': ma[-1],
            'diff_atual': diff[-1],
            'forca_tendencia': forca_tendencia,
            'aceleracao_momento': aceleracao_momento,
            'rsi_ma_ratio': rsi_ma_ratio,
            'diff_anterior': diff_anterior,
            'rsi_anterior': rsi_anterior,
            'ma_anterior': ma_anterior,
            'probabilidade_estimada': prob_estimada,
            'diff': diff.tolist()
        }
    
    def _decidir_sinal(self, metricas, previsao):
        """Decide sinal combinando análise técnica com ML"""
        score_tecnico = self._calcular_score_tecnico(metricas)
        prob_sucesso = previsao['probabilidade_sucesso']
        confianca_ml = previsao['confianca']
        
        if prob_sucesso > 0.75 and score_tecnico > 3 and confianca_ml > 0.7:
            return {'sinal': 'CALL_FORTE', 'confianca': 0.95, 'motivo': 'alinhamento_muito_forte',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        elif prob_sucesso > 0.65 and score_tecnico > 2:
            return {'sinal': 'CALL', 'confianca': 0.80, 'motivo': 'alinhamento_forte',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        elif prob_sucesso > 0.55 and score_tecnico > 0.5:
            return {'sinal': 'LEVE_CALL', 'confianca': 0.60, 'motivo': 'alinhamento_moderado',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        elif prob_sucesso < 0.25 and score_tecnico < -3 and confianca_ml > 0.7:
            return {'sinal': 'PUT_FORTE', 'confianca': 0.95, 'motivo': 'alinhamento_muito_forte_baixa',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        elif prob_sucesso < 0.35 and score_tecnico < -2:
            return {'sinal': 'PUT', 'confianca': 0.80, 'motivo': 'alinhamento_forte_baixa',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        elif prob_sucesso < 0.45 and score_tecnico < -0.5:
            return {'sinal': 'LEVE_PUT', 'confianca': 0.60, 'motivo': 'alinhamento_moderado_baixa',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        elif abs(prob_sucesso - 0.5) < 0.1 and abs(score_tecnico) < 1:
            return {'sinal': 'NEUTRO', 'confianca': 0.40, 'motivo': 'divergencia_ou_indefinicao',
                    'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
        else:
            if confianca_ml > 0.6:
                return {'sinal': 'CALL' if prob_sucesso > 0.5 else 'PUT', 'confianca': confianca_ml * 0.8,
                        'motivo': 'ml_orienta', 'prob_ml': prob_sucesso, 'confianca_ml': confianca_ml,
                        'score_tecnico': score_tecnico}
            else:
                return {'sinal': 'CALL' if score_tecnico > 0 else 'PUT' if score_tecnico < 0 else 'NEUTRO',
                        'confianca': 0.50, 'motivo': 'tecnico_orienta', 'prob_ml': prob_sucesso,
                        'confianca_ml': confianca_ml, 'score_tecnico': score_tecnico}
    
    def _calcular_score_tecnico(self, metricas):
        """Score técnico com mais fatores"""
        score = 0
        
        if metricas['slope'] > 0.2:
            score += 3
        elif metricas['slope'] > 0.1:
            score += 2
        elif metricas['slope'] > 0.05:
            score += 1
        elif metricas['slope'] < -0.2:
            score -= 3
        elif metricas['slope'] < -0.1:
            score -= 2
        elif metricas['slope'] < -0.05:
            score -= 1
        
        if metricas['velocidade'] > 0.15:
            score += 2
        elif metricas['velocidade'] > 0.05:
            score += 1
        elif metricas['velocidade'] < -0.15:
            score -= 2
        elif metricas['velocidade'] < -0.05:
            score -= 1
        
        if metricas['aceleracao'] > 0.1:
            score += 1
        elif metricas['aceleracao'] < -0.1:
            score -= 1
        
        if metricas['correlacao'] > 0.5:
            score += 1
        elif metricas['correlacao'] < -0.5:
            score -= 1
        
        score += metricas['cruzamento'] * 1
        
        if metricas.get('forca_tendencia', 0) > 0.3:
            score += 1
        elif metricas.get('forca_tendencia', 0) < -0.3:
            score -= 1
        
        return score
    
    # ==================== REGISTRO E ESTATÍSTICAS ====================
    
    def registrar_resultado(self, estado, lucro_percentual):
        """
        Registra resultado e treina novamente
        Aceita tanto dict quanto string JSON
        """
        # 🔥 CONVERTER string JSON para dict se necessário
        if isinstance(estado, str):
            try:
                estado_dict = json.loads(estado)
                print(f"✅ Estado convertido de string para dict")
            except json.JSONDecodeError as e:
                print(f"⚠️ Erro ao decodificar JSON: {e}")
                return
        else:
            estado_dict = estado
        
        if estado_dict is None:
            print("⚠️ Estado inválido")
            return
        
        # 🔥 VERIFICAR SE TEM 'metricas' - PODE ESTAR EM NÍVEIS DIFERENTES!
        if 'metricas' in estado_dict:
            metricas = estado_dict['metricas']
            previsao = estado_dict.get('previsao', {})
        elif 'sinal_final' in estado_dict and 'metricas' in estado_dict['sinal_final']:
            # Para o formato antigo que tem 'metricas' dentro de 'sinal_final'
            metricas = estado_dict['sinal_final']['metricas']
            previsao = estado_dict.get('previsao', {})
        else:
            print(f"⚠️ Estado sem 'metricas'")
            if isinstance(estado_dict, dict):
                print(f"   Chaves disponíveis: {list(estado_dict.keys())}")
            return
        
        registro = {
            'slope': metricas.get('slope', 0),
            'velocidade': metricas.get('velocidade', 0),
            'aceleracao': metricas.get('aceleracao', 0),
            'momento': metricas.get('momento', 0),
            'correlacao': metricas.get('correlacao', 0),
            'cruzamento': metricas.get('cruzamento', 0),
            'rsi_atual': metricas.get('rsi_atual', 50),
            'ma_atual': metricas.get('ma_atual', 50),
            'diff_atual': metricas.get('diff_atual', 0),
            'volatilidade': metricas.get('volatilidade', 1),
            'forca_tendencia': metricas.get('forca_tendencia', 0),
            'aceleracao_momento': metricas.get('aceleracao_momento', 0),
            'rsi_ma_ratio': metricas.get('rsi_ma_ratio', 0),
            'diff_anterior': metricas.get('diff_anterior', 0),
            'rsi_anterior': metricas.get('rsi_anterior', 0),
            'ma_anterior': metricas.get('ma_anterior', 0),
            'probabilidade_estimada': metricas.get('probabilidade_estimada', 0.5),
            'prob_ml': previsao.get('probabilidade_sucesso', 0.5) if previsao else 0.5,
            'confianca_ml': previsao.get('confianca', 0.5) if previsao else 0.5,
            'label': 1 if lucro_percentual > 0 else 0,
            'lucro': lucro_percentual,
            'timestamp': datetime.datetime.now()
        }
        
        self.historico_operacoes.append(registro)
        print(f"✅ Registro adicionado! Total: {len(self.historico_operacoes)}")
        
        if len(self.historico_operacoes) >= 30 and len(self.historico_operacoes) % 10 == 0:
            print(f"\n🔄 Retreinando com {len(self.historico_operacoes)} operações...")
            self.ensemble.treinar(self.historico_operacoes, epochs=50)
    
    def get_estatisticas(self):
        """Retorna estatísticas completas com tratamento seguro"""
        if len(self.historico_operacoes) == 0:
            return {
                'total_operacoes': 0,
                'taxa_acerto': 0.0,
                'lucro_medio': 0.0,
                'lucro_total': 0.0,
                'maior_lucro': 0.0,
                'maior_prejuizo': 0.0,
                'sharpe_ratio': 0.0
            }
        
        try:
            lucros = [op.get('lucro', 0) for op in self.historico_operacoes]
            acertos = sum(1 for op in self.historico_operacoes if op.get('label', 0) == 1)
            total = len(self.historico_operacoes)
            
            taxa_acerto = (acertos / total * 100) if total > 0 else 0
            lucro_medio = np.mean(lucros) if lucros else 0
            lucro_total = np.sum(lucros) if lucros else 0
            maior_lucro = max(lucros) if lucros else 0
            maior_prejuizo = min(lucros) if lucros else 0
            
            std_lucros = np.std(lucros) if lucros else 0
            sharpe_ratio = lucro_medio / (std_lucros + 0.001) if lucros else 0
            
            return {
                'total_operacoes': total,
                'taxa_acerto': taxa_acerto,
                'lucro_medio': lucro_medio,
                'lucro_total': lucro_total,
                'maior_lucro': maior_lucro,
                'maior_prejuizo': maior_prejuizo,
                'sharpe_ratio': sharpe_ratio
            }
        except Exception as e:
            print(f"⚠️ Erro ao calcular estatísticas: {e}")
            return {
                'total_operacoes': len(self.historico_operacoes),
                'taxa_acerto': 0.0,
                'lucro_medio': 0.0,
                'lucro_total': 0.0,
                'maior_lucro': 0.0,
                'maior_prejuizo': 0.0,
                'sharpe_ratio': 0.0
            }

# ==================== INSTÂNCIA GLOBAL ====================

# Cria instância global para uso direto
sistema_ia = SistemaOpcoesInteligente()

# Mantém compatibilidade com código que espera 'rede'
rede = sistema_ia

print("\n✅ cerebro.py carregado com sucesso!")
print(f"   📊 Histórico: {len(rede.historico_operacoes)} operações")
print(f"   📊 Modelo treinado: {rede.ensemble.is_trained}")
print(f"   📊 Pesos: {rede.ensemble.pesos_ensemble}")

# ==================== EXEMPLO DE USO ====================

if __name__ == "__main__":
    # Teste rápido
    dados_teste = {
        'rsi_list': [45, 47, 50, 52, 55, 58, 62],
        'ma_list': [43, 44, 45, 46, 47, 48, 49],
        'rsi_historico': list(range(40, 65))[:25],
        'ma_historico': list(range(35, 60))[:25],
        'preco_atual': 45.50
    }
    
    print("\n📊 Testando sistema...")
    
    # Testar método analisar (compatibilidade)
    try:
        estado = rede.analisar("TESTE", dados_teste)
        print(f"   ✅ analisar() - Sinal: {estado.get('decisao', 'N/A')}")
        print(f"   📋 Chaves: {list(estado.keys())}")
    except Exception as e:
        print(f"   ❌ Erro em analisar(): {e}")
    
    # Testar método analisar_opcao
    try:
        resultado = rede.analisar_opcao("TESTE", dados_teste)
        print(f"   ✅ analisar_opcao() - Sinal: {resultado.get('sinal', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Erro em analisar_opcao(): {e}")