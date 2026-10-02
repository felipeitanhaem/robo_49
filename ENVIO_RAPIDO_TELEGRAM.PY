

# import requests

# TOKEN = "7037935636:AAGRRB_bCxBAt23GCrjc7zvsCPrlEWQ9os8"
# CHAT_ID = "-1004493997590"

# def enviar_dados():
#     url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
#     dados = "VALE3 100 78.0 78.95 C; VALE3 900 0.62 0.74 V"
#     payload = {
#         "chat_id": CHAT_ID,
#         "text": dados
#     }
#     resposta = requests.post(url, json=payload)
#     print(resposta.json())  # opcional: ver o retorno da API

# if __name__ == "__main__":
#     enviar_dados()

# import requests
# from datetime import datetime

# TOKEN = "7037935636:AAGRRB_bCxBAt23GCrjc7zvsCPrlEWQ9os8"
# CHAT_ID = "-1004493997590"
# FIREBASE_URL = "https://swingtrade-8bda4-default-rtdb.firebaseio.com/carteira.json"

# def enviar_dados():
#     # SEU FORMATO COM C/V
#     dados = "VALE3 100 78.0 78.95 C; VALEU771 1000 0.62 0.85 V"
    
#     # 1. Manda no grupo (como já faz)
#     url_tg = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
#     r1 = requests.post(url_tg, json={"chat_id": CHAT_ID, "text": dados})
#     print("Telegram:", r1.json().get("ok"))
    
#     # 2. Salva no Firebase pro app ler (CORREÇÃO DO LOOP)
#     payload = {
#         "dados": dados,
#         "timestamp": datetime.now().isoformat()
#     }
#     r2 = requests.put(FIREBASE_URL, json=payload)
#     print("Firebase:", r2.json())
#     print("App atualizado com sucesso!")

# if __name__ == "__main__":
#     enviar_dados()


# import requests
# from datetime import datetime

# FIREBASE_URL = "https://swingtrade-8bda4-default-rtdb.firebaseio.com/carteira.json"
# dados = "VALE3 100 78.0 78.95 C; VALEU771 500 0.62 0.78 V"

# # Firebase - PUT com timestamp
# requests.put(FIREBASE_URL, json={"dados": dados, "timestamp": datetime.now().isoformat()})
# print("Enviado!")    


#import requests
# import datetime

# # SEU FIREBASE - já configurado
# FIREBASE_URL = "https://swingtrade-8bda4-default-rtdb.firebaseio.com/carteira.json"

# def enviar_dados():
#     # Formato com C e V
#     dados = "VALE3 100 78.0 78.95 C; VALEU771 500 0.62 0.74 V"
    
#     payload = {
#         "dados": dados,
#         "timestamp": datetime.datetime.now().isoformat()
#     }
    
#     r = requests.put(FIREBASE_URL, json=payload)
#     print("✅ App atualizado:", r.json())

# if __name__ == "__main__":
#     enviar_dados()




"""
1. Crie o Firebase (grátis):

Vai em https://console.firebase.google.com > Create project (nome: swingtrade)
No menu lateral: Build > Realtime Database > Create Database > escolhe USA > Start in test mode
Na aba Rules, deixa assim temporariamente:
JSON
Tree
Raw
▶
{
▶
"rules"
:
{
".read"
:
true,
".write"
:
true
}
}
Copia a URL que aparece no topo, tipo: https://seu-projeto-default-rtdb.firebaseio.com

"""




import requests
from datetime import datetime

FIREBASE_URL = "https://swingtrade-8bda4-default-rtdb.firebaseio.com/carteira.json"

dados = "VALE3 100 78.0 78.95 C 640.20; VALEU771 500 0.62 0.75 V 0.0"

# Firebase - PUT com timestamp
requests.put(FIREBASE_URL, json={"dados": dados, "timestamp": datetime.now().isoformat()})
print("Enviado!")


