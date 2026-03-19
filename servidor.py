import os
import asyncio
import websockets
import json
import http

# Banco de dados simplificado
bd = {
    "goku": {"nome": "Goku", "vida": 100, "energia": 50, "atq": 15, "def": 10, "mag": 35, "res": 15, "tecnica": "Kamehameha", "custo_tec": 20},
    "gojo": {"nome": "Satoru Gojo", "vida": 90, "energia": 60, "atq": 12, "def": 12, "mag": 40, "res": 25, "tecnica": "Vazio Roxo", "custo_tec": 30}
}

# Estado central do jogo
estado_jogo = {
    "j1": bd["goku"].copy(),
    "j2": bd["gojo"].copy(),
    "turno": 1,
    "vencedor": None
}

conexoes = {}

async def notificar_jogadores(log=""):
    mensagem = json.dumps({"tipo": "atualizacao", "estado": estado_jogo, "log": log})
    for conexao in conexoes.keys():
        await conexao.send(mensagem)

async def gerenciar_batalha(websocket):
    if "j1" not in conexoes.values():
        id_jogador = "j1"
    elif "j2" not in conexoes.values():
        id_jogador = "j2"
    else:
        await websocket.send(json.dumps({"tipo": "erro", "log": "A sala está cheia!"}))
        return

    conexoes[websocket] = id_jogador
    print(f"[{id_jogador}] Entrou na arena!")
    
    await websocket.send(json.dumps({"tipo": "identidade", "id": id_jogador}))
    await notificar_jogadores(f"{estado_jogo[id_jogador]['nome']} entrou na arena!")

    try:
        async for mensagem in websocket:
            dados = json.loads(mensagem)
            acao = dados.get("acao")
            
            if estado_jogo["vencedor"]:
                continue
                
            numero_jogador = 1 if id_jogador == "j1" else 2
            if estado_jogo["turno"] != numero_jogador:
                continue

            atacante = estado_jogo["j1"] if id_jogador == "j1" else estado_jogo["j2"]
            defensor = estado_jogo["j2"] if id_jogador == "j1" else estado_jogo["j1"]
            log_acao = ""

            if acao == 'fisico':
                dano = max(1, atacante['atq'] - defensor['def'])
                defensor['vida'] -= dano
                log_acao = f"💥 {atacante['nome']} deu um ataque físico causando {dano} de dano!"
            
            elif acao == 'magico':
                if atacante['energia'] >= atacante['custo_tec']:
                    atacante['energia'] -= atacante['custo_tec']
                    dano = max(1, atacante['mag'] - defensor['res'])
                    defensor['vida'] -= dano
                    log_acao = f"✨ {atacante['nome']} usou {atacante['tecnica']} causando {dano} de dano!"
                else:
                    log_acao = f"❌ {atacante['nome']} falhou a magia por falta de energia!"
            
            elif acao == 'focar':
                atacante['energia'] += 20
                log_acao = f"🔋 {atacante['nome']} focou e recuperou 20 de energia."

            if defensor['vida'] <= 0:
                defensor['vida'] = 0
                estado_jogo["vencedor"] = atacante['nome']
                log_acao += f" 🏆 VITÓRIA DE {atacante['nome']}!"

            estado_jogo["turno"] = 2 if estado_jogo["turno"] == 1 else 1
            await notificar_jogadores(log_acao)

    finally:
        print(f"[{id_jogador}] Saiu da arena.")
        del conexoes[websocket]

async def processar_requisicao(connection, request):
    # O handshake de um WebSocket sempre tem um cabeçalho "Upgrade"
    # Se não tiver, é o bot do Render fazendo Health Check.
    if "Upgrade" not in request.headers:
        # Devolvemos um "OK" simples para o Render ficar feliz e não derrubar o servidor
        return connection.respond(http.HTTPStatus.OK, "Servidor Vivo\n")
    
    # Retornar None faz com que o fluxo continue normalmente para a batalha
    return None

async def main():
    porta = int(os.environ.get("PORT", 8765))
    
    # Adicionamos o parâmetro process_request aqui dentro do serve
    async with websockets.serve(
        gerenciar_batalha, 
        "0.0.0.0", 
        porta, 
        process_request=processar_requisicao
    ):
        print(f"Servidor a correr na porta {porta}. À espera de lutadores...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
