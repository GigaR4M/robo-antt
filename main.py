import os
import pandas as pd
from playwright.sync_api import sync_playwright, Page
from dotenv import load_dotenv

# Carrega as variáveis do ficheiro .env para o ambiente
load_dotenv()

def fazer_login(pagina: Page, placa: str, nsolicitacao: str):
    """
    Realiza o login no sistema da ANTT e navega até a página de solicitações.
    """
    print("A aceder à página inicial...")
    pagina.goto("https://appweb1.antt.gov.br/autorizacaoDeViagem/AvPublico/inicial.asp")

    cnpj = os.getenv("CNPJ")
    codigo_acesso = os.getenv("CODIGO_ACESSO")

    # Verificação de segurança para garantir que as variáveis foram carregadas
    if not all([cnpj, codigo_acesso, placa, nsolicitacao]):
        print("ERRO CRÍTICO: Uma ou mais variáveis (CNPJ, CODIGO_ACESSO, PLACA_VEICULO, NUMERO_SOLICITACAO) não foram encontradas no ficheiro .env.")
        return None

    print("A preencher os dados de login...")
    pagina.locator('input[name="txtCNPJ"]').fill(cnpj)
    pagina.locator('input[name="txtPlacaVeiculo"]').fill(placa)
    pagina.locator('input[name="txtCodigoAcesso"]').fill(codigo_acesso)

    print("A entrar no sistema...")
    with pagina.expect_popup() as pagina2_info:
        pagina.get_by_role("button", name="Entrar").click()
    
    pagina2 = pagina2_info.value
    pagina2.wait_for_load_state("domcontentloaded")
    print("Login realizado com sucesso. A navegar para a autorização de viagem...")

    pagina2.get_by_role("link", name="Autorização de Viagem Comum").click()
    pagina2.get_by_role("row", name="Listar Solicitação/Autorizaçã").get_by_role("button").click()

    print(f"A procurar pela solicitação: {nsolicitacao}")
    pagina2.get_by_role("link", name=nsolicitacao).click()
    pagina2.get_by_role("button", name="Submit").nth(1).click()
    
    pagina2.goto("https://appweb1.antt.gov.br/autorizacaoDeViagem/AvPublico/relacao.asp")
    print("Página de inclusão de passageiros carregada.")
    
    return pagina2

def adicionar_passageiros(pagina: Page, caminho_csv: str):
    """
    Adiciona os passageiros a partir de um ficheiro CSV.
    """
    try:
        # Lê o CSV garantindo que colunas vazias fiquem como texto vazio
        df_passageiros = pd.read_csv(caminho_csv, dtype=str).fillna('')
    except FileNotFoundError:
        print(f"Erro: O ficheiro {caminho_csv} não foi encontrado.")
        return

    print(f"Encontrados {len(df_passageiros)} passageiros para adicionar.")

    for indice, passageiro in df_passageiros.iterrows():
        nome = passageiro["nome"]
        numero_documento = passageiro["numero_documento"]
        # A linha abaixo agora é segura por causa das alterações na leitura do CSV
        ntelefone = passageiro["ntelefone"] 
        
        print(f"A adicionar passageiro: {nome}")

        pagina.locator('input[name="txtPassageiro"]').fill(nome)
        pagina.locator("#cmbTipoDocumento1").select_option("14") 
        pagina.locator('input[name="txtIdentidade"]').fill(numero_documento)
        pagina.locator('input[name="txtOrgao"]').fill("RECEITA FEDERAL")
        
        # --- ALTERAÇÃO PRINCIPAL AQUI ---
        # Agora a variável 'ntelefone' conterá "" em vez de "nan"
        # quando o campo estiver vazio no CSV.
        pagina.locator("#telefone").fill(ntelefone)
        
        pagina.locator("#btnInc").click()
        pagina.wait_for_load_state("networkidle")

    print("Todos os passageiros foram adicionados com sucesso!")

def main():
    """
    Função principal que orquestra a automação.
    """
    # Lê todas as configurações do ficheiro .env
    placa_veiculo = os.getenv("PLACA_VEICULO")
    numero_solicitacao = os.getenv("NUMERO_SOLICITACAO")
    arquivo_passageiros = "passageiros.csv"

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=False)
        contexto = navegador.new_context()
        pagina_principal = contexto.new_page()

        try:
            pagina_passageiros = fazer_login(pagina_principal, placa_veiculo, numero_solicitacao)
            
            if pagina_passageiros:
                adicionar_passageiros(pagina_passageiros, arquivo_passageiros)
                print("Processo concluído. O navegador será fechado em 10 segundos.")
                pagina_passageiros.wait_for_timeout(10000)
            else:
                print("Não foi possível continuar devido a uma falha no login ou configuração.")

        except Exception as e:
            print(f"Ocorreu um erro durante a execução: {e}")
        finally:
            navegador.close()
            print("Navegador fechado.")

if __name__ == "__main__":
    main()