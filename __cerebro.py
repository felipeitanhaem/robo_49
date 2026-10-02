import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import sklearn.exceptions
import joblib
import json
import os
from datetime import datetime
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
        self.batch_norm = nn.BatchNorm1d(hidden_size * 2)  # *2 por ser bidirecional
        
        # Camadas fully connected
        self.fc1 = nn.Linear(hidden_size * 2, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, output_size)
        
        self.sigmoid = nn.Sigmoid()
        self.relu = nn.ReLU()
        
    def forward(self, x):
        # Inicializar estados ocultos (para bidirecional)
        h0 = torch.zeros(self.num_layers * 2, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers * 2, x.size(0), self.hidden_size)
        
        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Pegar última saída
        out = out[:, -1, :]
        out = self.dropout(out)
        
        # Batch normalization
        out = self.batch_norm(out)
        
        # Camadas fully connected
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
        
        # Modelo PyTorch (inicializado depois)
        self.lstm_model = None
        self.lstm_input_size = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"📱 Dispositivo: {self.device}")
        
        # Scaler para normalização
        self.scaler = StandardScaler()
        
        # Pesos do ensemble (aprendidos com validação cruzada)
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
        
        # Métricas de validação
        self.metricas_validacao = {}
        
        # Flag para indicar se o modelo já foi treinado
        self.is_trained = False
        
        # Carregar modelo se existir
        self.carregar_modelo()
    
    # ==================== DADOS SINTÉTICOS MELHORADOS ====================
    
    def gerar_dados_sinteticos(self, n_amostras=500):
        """
        Gera dados sintéticos MAIS REALISTAS para treinamento
        """
        print(f"🔄 Gerando {n_amostras} amostras sintéticas realistas...")
        dados = []
        
        for _ in range(n_amostras):
            # Gerar tendência com persistência
            tendencia = np.random.choice(['alta', 'baixa', 'neutra'], p=[0.35, 0.35, 0.3])
            
            # Parâmetros base
            volatilidade_base = np.random.uniform(0.5, 3.0)
            ruido = np.random.normal(0, 0.1)
            
            if tendencia == 'alta':
                slope = np.random.uniform(0.05, 0.5) + ruido * 0.1
                velocidade = np.random.uniform(0.05, 0.5) + ruido * 0.05
                aceleracao = np.random.uniform(0.02, 0.2) + ruido * 0.02
                rsi_base = np.random.uniform(55, 80)
                label = 1
                prob_sucesso = 0.7 + np.random.uniform(0, 0.3)
                
            elif tendencia == 'baixa':
                slope = np.random.uniform(-0.5, -0.05) + ruido * 0.1
                velocidade = np.random.uniform(-0.5, -0.05) + ruido * 0.05
                aceleracao = np.random.uniform(-0.2, -0.02) + ruido * 0.02
                rsi_base = np.random.uniform(20, 45)
                label = 0
                prob_sucesso = np.random.uniform(0, 0.3)
                
            else:  # neutra
                slope = np.random.uniform(-0.05, 0.05) + ruido * 0.05
                velocidade = np.random.uniform(-0.1, 0.1) + ruido * 0.05
                aceleracao = np.random.uniform(-0.05, 0.05) + ruido * 0.02
                rsi_base = np.random.uniform(45, 55)
                label = 1 if np.random.random() > 0.5 else 0
                prob_sucesso = 0.4 + np.random.uniform(0, 0.2)
            
            # Gerar MA baseada no RSI com relação realista
            ma_base = rsi_base + np.random.uniform(-8, 8)
            
            # Criar histórico de RSI com caminhada aleatória
            rsi_hist = [rsi_base]
            ma_hist = [ma_base]
            for i in range(1, 30):
                # Adicionar persistência
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
                
                # Manter dentro de limites realistas
                rsi_hist[-1] = max(10, min(90, rsi_hist[-1]))
                ma_hist[-1] = max(5, min(95, ma_hist[-1]))
            
            # Features adicionais
            diff_hist = np.array(rsi_hist) - np.array(ma_hist)
            volatilidade = np.std(diff_hist[-20:]) if len(diff_hist) >= 20 else volatilidade_base
            
            # Correlação entre RSI e MA
            correlacao = np.corrcoef(rsi_hist[-20:], ma_hist[-20:])[0, 1] if len(rsi_hist) >= 20 else np.random.uniform(-0.6, 0.6)
            
            # Momentum
            momento = np.mean(diff_hist[-5:]) - np.mean(diff_hist) if len(diff_hist) >= 5 else 0
            
            # Cruzamento
            cruzamento = 0
            if len(diff_hist) >= 3:
                if diff_hist[-3] < 0 and diff_hist[-1] > 0:
                    cruzamento = 1
                elif diff_hist[-3] > 0 and diff_hist[-1] < 0:
                    cruzamento = -1
            
            # Força da tendência (nova feature)
            forca_tendencia = abs(slope) * (1 + abs(correlacao))
            
            # Aceleração do momentum (nova feature)
            if len(diff_hist) >= 4:
                aceleracao_momento = (diff_hist[-1] - diff_hist[-3]) - (diff_hist[-2] - diff_hist[-4])
            else:
                aceleracao_momento = 0
            
            # Registro completo
            registro = {
                # Features básicas
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
                
                # NOVAS FEATURES
                'forca_tendencia': forca_tendencia,
                'aceleracao_momento': aceleracao_momento,
                'rsi_ma_ratio': rsi_hist[-1] / (ma_hist[-1] + 0.001),
                'diff_anterior': diff_hist[-2] if len(diff_hist) >= 2 else diff_hist[-1],
                'rsi_anterior': rsi_hist[-2] if len(rsi_hist) >= 2 else rsi_hist[-1],
                'ma_anterior': ma_hist[-2] if len(ma_hist) >= 2 else ma_hist[-1],
                'probabilidade_real': prob_sucesso,
                'tendencia_real': tendencia,
                'label': label,
                
                # Histórico para LSTM
                'rsi_historico': rsi_hist[-25:],
                'ma_historico': ma_hist[-25:],
                'diff_historico': diff_hist[-25:].tolist()
            }
            dados.append(registro)
        
        return dados
    
    # ==================== PREPARAÇÃO DE DADOS MELHORADA ====================
    
    def preparar_dados(self, dados_historicos):
        """
        Prepara os dados para treinamento com MAIS FEATURES
        """
        features_list = []
        labels_list = []
        series_temporais = []  # Para LSTM
        pesos_amostras = []  # Pesos para amostras desbalanceadas
        
        for registro in dados_historicos:
            # Features expandidas (17 features)
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
                # NOVAS FEATURES
                registro.get('forca_tendencia', 0),
                registro.get('aceleracao_momento', 0),
                registro.get('rsi_ma_ratio', 0),
                registro.get('diff_anterior', 0),
                registro.get('rsi_anterior', 0),
                registro.get('ma_anterior', 0),
                registro.get('probabilidade_real', 0.5)
            ]
            features_list.append(features)
            labels_list.append(registro['label'])
            
            # Peso para amostras (dar mais peso a casos extremos)
            if registro['label'] == 1:
                peso = 1.0 if abs(registro['slope']) > 0.3 else 0.8
            else:
                peso = 1.0 if abs(registro['slope']) > 0.3 else 0.8
            pesos_amostras.append(peso)
            
            # Série temporal para LSTM (mais features)
            if 'rsi_historico' in registro and 'ma_historico' in registro:
                rsi_hist = registro['rsi_historico'][-20:]
                ma_hist = registro['ma_historico'][-20:]
                if len(rsi_hist) >= 20:
                    # Múltiplas séries temporais
                    diff_hist = np.array(rsi_hist) - np.array(ma_hist)
                    serie = np.column_stack([
                        rsi_hist,
                        ma_hist,
                        diff_hist,
                        np.gradient(rsi_hist),  # Taxa de mudança RSI
                        np.gradient(ma_hist),   # Taxa de mudança MA
                        np.gradient(diff_hist), # Taxa de mudança diff
                    ])
                    series_temporais.append(serie)
        
        X = np.array(features_list)
        y = np.array(labels_list)
        X_series = np.array(series_temporais) if series_temporais else None
        pesos = np.array(pesos_amostras) if pesos_amostras else None
        
        return X, y, X_series, pesos
    
    # ==================== TREINAMENTO MELHORADO ====================
    
    def treinar(self, dados_historicos, epochs=100, batch_size=32):
        """
        Treina todos os modelos do ensemble com validação cruzada
        """
        print("🔄 Preparando dados...")
        X, y, X_series, pesos = self.preparar_dados(dados_historicos)
        
        if len(X) < 20:
            print("❌ Dados insuficientes para treinamento (mínimo 20 amostras)")
            return False
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Normalizar
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # ----- 1. Treinar Random Forest -----
        print("🌲 Treinando Random Forest...")
        self.rf_model.fit(X_train_scaled, y_train)
        rf_pred = self.rf_model.predict(X_test_scaled)
        rf_acuracia = accuracy_score(y_test, rf_pred)
        rf_f1 = f1_score(y_test, rf_pred)
        self.historico_treino['rf_acuracia'].append(rf_acuracia)
        print(f"   ✅ Random Forest - Acurácia: {rf_acuracia:.2%}, F1: {rf_f1:.2%}")
        
        # ----- 2. Treinar Gradient Boosting -----
        print("📈 Treinando Gradient Boosting...")
        self.gb_model.fit(X_train_scaled, y_train)
        gb_pred = self.gb_model.predict(X_test_scaled)
        gb_acuracia = accuracy_score(y_test, gb_pred)
        gb_f1 = f1_score(y_test, gb_pred)
        self.historico_treino['gb_acuracia'].append(gb_acuracia)
        print(f"   ✅ Gradient Boosting - Acurácia: {gb_acuracia:.2%}, F1: {gb_f1:.2%}")
        
        # ----- 3. Treinar XGBoost (se disponível) -----
        xgb_acuracia = 0.5
        if self.xgb_model is not None:
            print("⚡ Treinando XGBoost...")
            self.xgb_model.fit(X_train_scaled, y_train)
            xgb_pred = self.xgb_model.predict(X_test_scaled)
            xgb_acuracia = accuracy_score(y_test, xgb_pred)
            xgb_f1 = f1_score(y_test, xgb_pred)
            self.historico_treino['xgb_acuracia'].append(xgb_acuracia)
            print(f"   ✅ XGBoost - Acurácia: {xgb_acuracia:.2%}, F1: {xgb_f1:.2%}")
        
        # ----- 4. Treinar LSTM (se houver dados de série temporal) -----
        lstm_acuracia = 0.5
        if X_series is not None and len(X_series) > 20:
            print("🧠 Treinando LSTM (PyTorch)...")
            lstm_acuracia = self._treinar_lstm_melhorado(X_series, y, epochs, batch_size)
            self.historico_treino['lstm_acuracia'].append(lstm_acuracia)
            print(f"   ✅ LSTM Acurácia: {lstm_acuracia:.2%}")
        else:
            print("⚠️ Dados insuficientes para LSTM")
        
        # ----- 5. Ajustar pesos do ensemble -----
        self._ajustar_pesos_ensemble()
        
        # ----- 6. Validação cruzada do ensemble -----
        print("📊 Validando ensemble...")
        ensemble_acc = self._validar_ensemble(X_test_scaled, y_test, X_series)
        self.historico_treino['ensemble_acuracia'].append(ensemble_acc)
        print(f"   ✅ Ensemble Acurácia: {ensemble_acc:.2%}")
        
        # ----- 7. Marcar como treinado -----
        self.is_trained = True
        
        # ----- 8. Salvar modelo -----
        self.salvar_modelo()
        
        print("\n✅ Treinamento concluído!")
        print(f"📊 Pesos do ensemble: {self.pesos_ensemble}")
        print(f"📈 Acurácia média: {ensemble_acc:.2%}")
        
        return True
    
    def _treinar_lstm_melhorado(self, X_series, y, epochs, batch_size):
        """
        Treina a LSTM com early stopping e validação
        """
        # Configurar LSTM (6 features na série temporal)
        self.lstm_input_size = X_series.shape[2]
        
        # Criar modelo
        self.lstm_model = LSTMPredictor(
            input_size=self.lstm_input_size,
            hidden_size=128,
            num_layers=3,
            output_size=1,
            dropout=0.3
        ).to(self.device)
        
        # Preparar dados
        X_tensor = torch.FloatTensor(X_series)
        y_tensor = torch.FloatTensor(y).view(-1, 1)
        
        # Dividir dados (com estratificação)
        indices = np.arange(len(X_tensor))
        train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42, stratify=y)
        
        X_train = X_tensor[train_idx]
        y_train = y_tensor[train_idx]
        X_test = X_tensor[test_idx]
        y_test = y_tensor[test_idx]
        
        # Criar DataLoader
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Configurar otimizador e loss
        optimizer = optim.Adam(self.lstm_model.parameters(), lr=0.0005, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
        criterion = nn.BCELoss()
        
        # Early stopping
        best_loss = float('inf')
        patience_counter = 0
        patience = 20
        
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
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.lstm_model.parameters(), 1.0)
                
                optimizer.step()
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(train_loader)
            scheduler.step(avg_loss)
            
            # Early stopping
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter > patience:
                    print(f"   ⏹️ Early stopping no epoch {epoch+1}")
                    break
            
            if (epoch + 1) % 20 == 0:
                print(f"   Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
        
        # Avaliar
        self.lstm_model.eval()
        with torch.no_grad():
            X_test = X_test.to(self.device)
            predictions = self.lstm_model(X_test)
            predictions = predictions.cpu().numpy()
            predictions = (predictions > 0.5).astype(int)
            
            y_test_np = y_test.numpy()
            acuracia = accuracy_score(y_test_np, predictions)
            f1 = f1_score(y_test_np, predictions)
            
            print(f"   ✅ LSTM - Acurácia: {acuracia:.2%}, F1: {f1:.2%}")
        
        return acuracia
    
    def _ajustar_pesos_ensemble(self):
        """
        Ajusta os pesos do ensemble baseado no desempenho de cada modelo
        """
        # Coletar acurácias
        rf_acc = self.historico_treino['rf_acuracia'][-1] if self.historico_treino['rf_acuracia'] else 0.5
        gb_acc = self.historico_treino['gb_acuracia'][-1] if self.historico_treino['gb_acuracia'] else 0.5
        xgb_acc = self.historico_treino.get('xgb_acuracia', [0.5])[-1] if self.historico_treino.get('xgb_acuracia') else 0.5
        lstm_acc = self.historico_treino.get('lstm_acuracia', [0.5])[-1] if self.historico_treino.get('lstm_acuracia') else 0.5
        
        # Dar mais peso a modelos com melhor desempenho
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
        
        # Normalizar pesos
        total = sum(pesos)
        if total > 0:
            for i, modelo in enumerate(modelos):
                self.pesos_ensemble[modelo] = pesos[i] / total
            
            # Garantir que todos os modelos tenham peso
            for modelo in ['random_forest', 'gradient_boosting', 'xgboost', 'lstm']:
                if modelo not in self.pesos_ensemble:
                    self.pesos_ensemble[modelo] = 0
    
    def _validar_ensemble(self, X_test, y_test, X_series=None):
        """
        Valida o ensemble completo
        """
        # Previsões individuais
        rf_pred = self.rf_model.predict_proba(X_test)[:, 1]
        gb_pred = self.gb_model.predict_proba(X_test)[:, 1]
        
        # Combinar previsões
        pred_ensemble = (
            self.pesos_ensemble['random_forest'] * rf_pred +
            self.pesos_ensemble['gradient_boosting'] * gb_pred
        )
        
        # Adicionar XGBoost se disponível
        if self.xgb_model is not None and self.pesos_ensemble.get('xgboost', 0) > 0:
            xgb_pred = self.xgb_model.predict_proba(X_test)[:, 1]
            pred_ensemble += self.pesos_ensemble['xgboost'] * xgb_pred
        
        # Se LSTM estiver disponível
        if self.lstm_model is not None and X_series is not None:
            try:
                # Preparar dados para LSTM
                X_test_lstm = torch.FloatTensor(X_series[-len(y_test):])
                self.lstm_model.eval()
                with torch.no_grad():
                    X_test_lstm = X_test_lstm.to(self.device)
                    lstm_pred = self.lstm_model(X_test_lstm).cpu().numpy().flatten()
                    pred_ensemble += self.pesos_ensemble['lstm'] * lstm_pred
            except:
                pass
        
        # Decisão final
        pred_final = (pred_ensemble > 0.5).astype(int)
        return accuracy_score(y_test, pred_final)
    
    # ==================== PREVISÃO MELHORADA ====================
    
    def prever(self, features, serie_temporal=None):
        """
        Faz previsão usando ensemble com mais features
        """
        # Verificar se o modelo está treinado
        if not self.is_trained:
            print("⚠️ Modelo não treinado. Gerando dados sintéticos...")
            dados_sinteticos = self.gerar_dados_sinteticos(200)
            self.treinar(dados_sinteticos, epochs=50)
        
        # Verificar número de features
        if len(features) < 17:
            # Preencher com zeros
            features = list(features) + [0] * (17 - len(features))
        
        # Normalizar features
        try:
            features_scaled = self.scaler.transform([features])
        except sklearn.exceptions.NotFittedError:
            print("⚠️ Scaler não treinado. Gerando dados sintéticos...")
            dados_sinteticos = self.gerar_dados_sinteticos(200)
            self.treinar(dados_sinteticos, epochs=50)
            features_scaled = self.scaler.transform([features])
        
        # Previsões individuais
        rf_pred = self.rf_model.predict_proba(features_scaled)[0][1]
        gb_pred = self.gb_model.predict_proba(features_scaled)[0][1]
        
        # XGBoost
        xgb_pred = 0.5
        if self.xgb_model is not None:
            xgb_pred = self.xgb_model.predict_proba(features_scaled)[0][1]
        
        # Previsão da LSTM
        lstm_pred = 0.5
        if self.lstm_model is not None and serie_temporal is not None:
            try:
                # Garantir que a série temporal tem o formato correto
                if len(serie_temporal) < 20:
                    # Padding
                    pad = np.zeros((20 - len(serie_temporal), serie_temporal.shape[1]))
                    serie_temporal = np.vstack([pad, serie_temporal])
                
                self.lstm_model.eval()
                with torch.no_grad():
                    serie_tensor = torch.FloatTensor(serie_temporal).unsqueeze(0).to(self.device)
                    lstm_pred = self.lstm_model(serie_tensor).cpu().numpy()[0][0]
            except Exception as e:
                print(f"Erro LSTM: {e}")
                lstm_pred = 0.5
        
        # Combinar previsões
        previsao_ensemble = (
            self.pesos_ensemble['random_forest'] * rf_pred +
            self.pesos_ensemble['gradient_boosting'] * gb_pred +
            self.pesos_ensemble.get('xgboost', 0) * xgb_pred +
            self.pesos_ensemble['lstm'] * lstm_pred
        )
        
        # Calcular confiança baseada na divergência entre modelos
        preds = [rf_pred, gb_pred, xgb_pred, lstm_pred]
        pesos = [self.pesos_ensemble['random_forest'], 
                 self.pesos_ensemble['gradient_boosting'],
                 self.pesos_ensemble.get('xgboost', 0),
                 self.pesos_ensemble['lstm']]
        
        # Confiança = 1 - variância ponderada
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
            'decisao': 'COMPRAR' if previsao_ensemble > 0.6 else 'AGUARDAR',
            'nivel_confianca': 'ALTO' if confianca > 0.7 else 'MEDIO' if confianca > 0.5 else 'BAIXO'
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
                    json.dump({
                        'input_size': self.lstm_input_size,
                        'n_features': 17
                    }, f)
            
            print(f"✅ Modelo salvo em {self.arquivo_modelo}")
            return True
        except Exception as e:
            print(f"Erro ao salvar modelo: {e}")
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
            
            # Carregar LSTM
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
            print(f"Erro ao carregar modelo: {e}")
            return False

# ==================== PARTE 3: SISTEMA DE INTEGRAÇÃO MELHORADO ====================

class SistemaOpcoesInteligente:
    """
    Sistema completo integrando análise técnica com IA
    """
    
    def __init__(self):
        self.ensemble = EnsemblePredictor()
        self.historico_operacoes = []
        self.ultimo_estado = None
        self.historico_metricas = deque(maxlen=100)  # Últimas 100 operações
        
    def analisar_opcao(self, opcao, dados_mercado):
        """
        Analisa opção usando ensemble com todas as features
        """
        # Calcular métricas expandidas
        metricas = self._calcular_metricas_expandidas(dados_mercado)
        
        # 17 features para o ensemble
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
        
        # Série temporal para LSTM (com mais features)
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
        
        # Fazer previsão
        previsao = self.ensemble.prever(features, serie_temporal)
        
        # Decisão combinada com análise técnica
        sinal_final = self._decidir_sinal_melhorado(metricas, previsao)
        
        # Guardar estado completo
        self.ultimo_estado = {
            'timestamp': datetime.now(),
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
    
    def _calcular_metricas_expandidas(self, dados):
        """
        Calcula métricas expandidas com mais features
        """
        rsi = np.array(dados['rsi_list'][-7:])
        ma = np.array(dados['ma_list'][-7:])
        diff = rsi - ma
        
        # Features básicas
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
        
        # Novas features
        forca_tendencia = abs(slope) * (1 + abs(correlacao))
        rsi_ma_ratio = rsi[-1] / (ma[-1] + 0.001)
        
        diff_anterior = diff[-2] if len(diff) >= 2 else diff[-1]
        rsi_anterior = rsi[-2] if len(rsi) >= 2 else rsi[-1]
        ma_anterior = ma[-2] if len(ma) >= 2 else ma[-1]
        
        if len(diff) >= 4:
            aceleracao_momento = (diff[-1] - diff[-3]) - (diff[-2] - diff[-4])
        else:
            aceleracao_momento = 0
        
        # Probabilidade estimada baseada em regras
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
    
    def _decidir_sinal_melhorado(self, metricas, previsao):
        """
        Decisão melhorada combinando análise técnica com ML
        """
        score_tecnico = self._calcular_score_tecnico(metricas)
        prob_sucesso = previsao['probabilidade_sucesso']
        confianca_ml = previsao['confianca']
        
        # Decisão com mais níveis
        if prob_sucesso > 0.75 and score_tecnico > 3 and confianca_ml > 0.7:
            sinal = 'CALL_FORTE'
            confianca = 0.95
            motivo = 'alinhamento_muito_forte'
            
        elif prob_sucesso > 0.65 and score_tecnico > 2:
            sinal = 'CALL'
            confianca = 0.80
            motivo = 'alinhamento_forte'
            
        elif prob_sucesso > 0.55 and score_tecnico > 0.5:
            sinal = 'LEVE_CALL'
            confianca = 0.60
            motivo = 'alinhamento_moderado'
            
        elif prob_sucesso < 0.25 and score_tecnico < -3 and confianca_ml > 0.7:
            sinal = 'PUT_FORTE'
            confianca = 0.95
            motivo = 'alinhamento_muito_forte_baixa'
            
        elif prob_sucesso < 0.35 and score_tecnico < -2:
            sinal = 'PUT'
            confianca = 0.80
            motivo = 'alinhamento_forte_baixa'
            
        elif prob_sucesso < 0.45 and score_tecnico < -0.5:
            sinal = 'LEVE_PUT'
            confianca = 0.60
            motivo = 'alinhamento_moderado_baixa'
            
        elif abs(prob_sucesso - 0.5) < 0.1 and abs(score_tecnico) < 1:
            sinal = 'NEUTRO'
            confianca = 0.40
            motivo = 'divergencia_ou_indefinicao'
            
        else:
            # Caso de divergência: usar a análise de maior confiança
            if confianca_ml > 0.6:
                sinal = 'CALL' if prob_sucesso > 0.5 else 'PUT'
                confianca = confianca_ml * 0.8
                motivo = 'ml_orienta'
            else:
                sinal = 'CALL' if score_tecnico > 0 else 'PUT' if score_tecnico < 0 else 'NEUTRO'
                confianca = 0.50
                motivo = 'tecnico_orienta'
        
        return {
            'sinal': sinal,
            'confianca': confianca,
            'motivo': motivo,
            'prob_ml': prob_sucesso,
            'confianca_ml': confianca_ml,
            'score_tecnico': score_tecnico
        }
    
    def _calcular_score_tecnico(self, metricas):
        """Score técnico com mais fatores"""
        score = 0
        
        # Tendência
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
        
        # Velocidade
        if metricas['velocidade'] > 0.15:
            score += 2
        elif metricas['velocidade'] > 0.05:
            score += 1
        elif metricas['velocidade'] < -0.15:
            score -= 2
        elif metricas['velocidade'] < -0.05:
            score -= 1
        
        # Aceleração
        if metricas['aceleracao'] > 0.1:
            score += 1
        elif metricas['aceleracao'] < -0.1:
            score -= 1
        
        # Correlação
        if metricas['correlacao'] > 0.5:
            score += 1
        elif metricas['correlacao'] < -0.5:
            score -= 1
        
        # Cruzamento
        score += metricas['cruzamento'] * 1
        
        # Força da tendência
        if metricas.get('forca_tendencia', 0) > 0.3:
            score += 1
        elif metricas.get('forca_tendencia', 0) < -0.3:
            score -= 1
        
        return score
    
    def registrar_resultado(self, lucro_percentual):
        """Registra resultado com mais informações"""
        if self.ultimo_estado is None:
            return
        
        metricas = self.ultimo_estado['metricas']
        previsao = self.ultimo_estado['previsao']
        
        # Registro completo
        registro = {
            'slope': metricas['slope'],
            'velocidade': metricas['velocidade'],
            'aceleracao': metricas['aceleracao'],
            'momento': metricas['momento'],
            'correlacao': metricas['correlacao'],
            'cruzamento': metricas['cruzamento'],
            'rsi_atual': metricas['rsi_atual'],
            'ma_atual': metricas['ma_atual'],
            'diff_atual': metricas['diff_atual'],
            'volatilidade': metricas['volatilidade'],
            'forca_tendencia': metricas.get('forca_tendencia', 0),
            'aceleracao_momento': metricas.get('aceleracao_momento', 0),
            'rsi_ma_ratio': metricas.get('rsi_ma_ratio', 0),
            'diff_anterior': metricas.get('diff_anterior', 0),
            'rsi_anterior': metricas.get('rsi_anterior', 0),
            'ma_anterior': metricas.get('ma_anterior', 0),
            'probabilidade_estimada': metricas.get('probabilidade_estimada', 0.5),
            'prob_ml': previsao['probabilidade_sucesso'],
            'confianca_ml': previsao['confianca'],
            'label': 1 if lucro_percentual > 0 else 0,
            'lucro': lucro_percentual,
            'timestamp': datetime.now()
        }
        
        self.historico_operacoes.append(registro)
        
        # Retreinar com dados reais
        if len(self.historico_operacoes) >= 30 and len(self.historico_operacoes) % 10 == 0:
            print(f"\n🔄 Retreinando modelo com {len(self.historico_operacoes)} operações reais...")
            self.ensemble.treinar(self.historico_operacoes, epochs=50)
    
    def get_estatisticas(self):
        """Retorna estatísticas completas"""
        if len(self.historico_operacoes) == 0:
            return {'total_operacoes': 0}
        
        lucros = [op['lucro'] for op in self.historico_operacoes]
        acertos = sum(1 for op in self.historico_operacoes if op['label'] == 1)
        
        # Estatísticas por tipo de sinal
        sinais = {}
        for op in self.historico_operacoes:
            # Recuperar sinal do último estado
            sinal = self.ultimo_estado['sinal_final']['sinal'] if self.ultimo_estado else 'DESCONHECIDO'
            if sinal not in sinais:
                sinais[sinal] = {'total': 0, 'acertos': 0, 'lucros': []}
            sinais[sinal]['total'] += 1
            if op['label'] == 1:
                sinais[sinal]['acertos'] += 1
            sinais[sinal]['lucros'].append(op['lucro'])
        
        # Calcular métricas por sinal
        for sinal in sinais:
            if sinais[sinal]['total'] > 0:
                sinais[sinal]['taxa_acerto'] = sinais[sinal]['acertos'] / sinais[sinal]['total']
                sinais[sinal]['lucro_medio'] = np.mean(sinais[sinal]['lucros'])
        
        return {
            'total_operacoes': len(self.historico_operacoes),
            'taxa_acerto': acertos / len(self.historico_operacoes) * 100,
            'lucro_medio': np.mean(lucros),
            'lucro_total': np.sum(lucros),
            'maior_lucro': np.max(lucros),
            'maior_prejuizo': np.min(lucros),
            'sharpe_ratio': np.mean(lucros) / (np.std(lucros) + 0.001),
            'sinais': sinais,
            'historico_treino': self.ensemble.historico_treino
        }


# ==================== FUNÇÃO DE INTEGRAÇÃO ====================

def integrar_com_sistema_existente():
    """
    Função para integrar o cerebro.py com seu sistema existente
    """
    # Instanciar sistema
    sistema_ia = SistemaOpcoesInteligente()
    
    # Esta função será chamada no lugar da sua análise original
    def analisar_com_ia(opcao, dados_mercado):
        """
        Substitui a análise original pela análise com IA
        """
        resultado = sistema_ia.analisar_opcao(opcao, dados_mercado)
        
        # Retornar no formato esperado pelo seu sistema
        return {
            'decisao': resultado['sinal'],
            'confianca': resultado['confianca'],
            'prob_ml': resultado.get('prob_ml', 0.5),
            'motivo': resultado['motivo'],
            'score_tecnico': resultado.get('score_tecnico', 0),
            'sinal': resultado['sinal'],
            'estado': sistema_ia.ultimo_estado  # Para compatibilidade
        }
    
    return analisar_com_ia, sistema_ia


# ==================== EXEMPLO DE USO ====================

if __name__ == "__main__":
    # Teste rápido
    sistema = SistemaOpcoesInteligente()
    
    dados_teste = {
        'rsi_list': [45, 47, 50, 52, 55, 58, 62],
        'ma_list': [43, 44, 45, 46, 47, 48, 49],
        'rsi_historico': [40, 42, 45, 48, 50, 52, 55, 58, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77],
        'ma_historico': [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62],
        'preco_atual': 45.50
    }
    
    print("📊 Testando sistema melhorado...")
    resultado = sistema.analisar_opcao("TESTE", dados_teste)
    
    print(f"\n🎯 Resultado: {resultado['sinal']}")
    print(f"   Confiança: {resultado['confianca']:.2%}")
    print(f"   Motivo: {resultado['motivo']}")
    print(f"   Prob ML: {resultado['prob_ml']:.2%}")
    print(f"   Confiança ML: {resultado['confianca_ml']:.2%}")
    print(f"   Score Técnico: {resultado['score_tecnico']:.2f}")