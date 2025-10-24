import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sqlite3
import base64
import os
import zipfile
import hashlib

# Configuração da página para melhor responsividade
st.set_page_config(
    page_title="Livro Caixa",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para melhor responsividade
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stDataFrame {
        font-size: 0.9rem;
    }
    @media (max-width: 768px) {
        .stDataFrame {
            font-size: 0.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTES PARA PERMISSÕES
PERMISSOES = {
    'admin': 'Administrador',
    'editor': 'Editor', 
    'visualizador': 'Apenas Visualização'
}

# Funções de autenticação MODIFICADAS
def init_auth_db():
    """Inicializa a tabela de usuários com permissões"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            permissao TEXT NOT NULL DEFAULT 'visualizador',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir usuários padrão se não existirem
    c.execute('SELECT COUNT(*) FROM usuarios WHERE username = ?', ('admin',))
    if c.fetchone()[0] == 0:
        # Senha padrão: "admin123"
        password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute('INSERT INTO usuarios (username, password_hash, permissao) VALUES (?, ?, ?)', 
                 ('admin', password_hash, 'admin'))
        
        # Usuário visualizador padrão
        password_hash_viewer = hashlib.sha256('visual123'.encode()).hexdigest()
        c.execute('INSERT INTO usuarios (username, password_hash, permissao) VALUES (?, ?, ?)', 
                 ('visual', password_hash_viewer, 'visualizador'))
    
    conn.commit()
    conn.close()

def verify_password(password, password_hash):
    """Verifica se a senha está correta"""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash

def login_user(username, password):
    """Faz login do usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('SELECT password_hash, permissao FROM usuarios WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if result and verify_password(password, result[0]):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.permissao = result[1]  # Salvar a permissão na sessão
        return True
    return False

def logout_user():
    """Faz logout do usuário"""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.permissao = None

def change_password(username, new_password):
    """Altera a senha do usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    c.execute('UPDATE usuarios SET password_hash = ? WHERE username = ?', 
             (password_hash, username))
    conn.commit()
    conn.close()

def create_user(username, password, permissao='visualizador'):
    """Cria um novo usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        c.execute('INSERT INTO usuarios (username, password_hash, permissao) VALUES (?, ?, ?)', 
                 (username, password_hash, permissao))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Usuário já existe
    except Exception as e:
        return False
    finally:
        conn.close()

def get_all_users():
    """Busca todos os usuários (apenas para admin)"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('SELECT username, permissao, created_at FROM usuarios ORDER BY created_at')
    users = c.fetchall()
    conn.close()
    
    return users

def update_user_permission(username, permissao):
    """Atualiza a permissão de um usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    try:
        c.execute('UPDATE usuarios SET permissao = ? WHERE username = ?', (permissao, username))
        conn.commit()
        return True, "Permissão atualizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar permissão: {e}"
    finally:
        conn.close()

def delete_user(username):
    """Exclui um usuário (apenas para admin)"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    try:
        # Não permitir excluir o próprio usuário
        if username == st.session_state.username:
            return False, "Não é possível excluir seu próprio usuário!"
        
        c.execute('DELETE FROM usuarios WHERE username = ?', (username,))
        conn.commit()
        return True, "Usuário excluído com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir usuário: {e}"
    finally:
        conn.close()

# Função para verificar permissões
def user_can_edit():
    """Verifica se o usuário tem permissão para editar"""
    return st.session_state.get('permissao') in ['admin', 'editor']

def user_is_admin():
    """Verifica se o usuário é administrador"""
    return st.session_state.get('permissao') == 'admin'

# ... (o restante das funções permanecem iguais: carregar_imagem_logo, init_db, get_lancamentos_mes, etc.)

# MODIFICAÇÕES NA INTERFACE:

# Na página de Login - Modificar o formulário de criar usuário:
if not st.session_state.logged_in:
    # ... (código do login existente)
    
    # Criar novo usuário (apenas na página de login)
    with st.expander("👥 Criar Novo Usuário"):
        with st.form("create_user_form"):
            st.subheader("Novo Usuário")
            new_username = st.text_input("Novo Usuário", placeholder="Digite o nome de usuário")
            new_password = st.text_input("Nova Senha", type="password", placeholder="Digite a senha")
            confirm_password = st.text_input("Confirmar Senha", type="password", placeholder="Confirme a senha")
            
            # Apenas admin pode definir permissões ao criar usuário
            if st.session_state.get('logged_in') and user_is_admin():
                permissao = st.selectbox("Permissão", options=list(PERMISSOES.keys()), 
                                       format_func=lambda x: PERMISSOES[x])
            else:
                permissao = 'visualizador'  # Padrão para novos usuários
            
            create_submitted = st.form_submit_button("👤 Criar Usuário", use_container_width=True)
            
            if create_submitted:
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        if create_user(new_username, new_password, permissao):
                            st.success(f"✅ Usuário '{new_username}' criado com sucesso!")
                        else:
                            st.error("❌ Erro ao criar usuário. Nome de usuário já existe.")
                    else:
                        st.error("❌ As senhas não coincidem!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")

# Na sidebar - Adicionar informações de permissão:
with st.sidebar:
    # ... (código da sidebar existente)
    
    # Informações do usuário logado COM PERMISSÃO
    st.sidebar.markdown("---")
    st.sidebar.success(f"👤 **Usuário:** {st.session_state.username}")
    st.sidebar.info(f"🔐 **Permissão:** {PERMISSOES.get(st.session_state.permissao, 'Desconhecida')}")
    
    # ... (restante da sidebar)

# MODIFICAÇÕES NAS PÁGINAS PARA IMPLEMENTAR RESTRIÇÕES:

# Página: Contas
elif pagina == "Contas":
    st.title("📝 Contas")
    
    # Buscar contas do banco
    contas = get_contas()
    
    # Apenas usuários com permissão de edição podem adicionar contas
    if user_can_edit():
        st.subheader("➕ Adicionar Nova Conta")
        
        nova_conta = st.text_input("**Nome da Nova Conta**", placeholder="Ex: Salários, Aluguel, Vendas...")
        
        if st.button("✅ Adicionar Conta", use_container_width=True) and nova_conta:
            adicionar_conta(nova_conta)
            st.rerun()
    else:
        st.info("👀 **Modo de Visualização** - Você pode apenas visualizar as contas existentes.")

# Página: Lançamentos - ADICIONAR VERIFICAÇÕES DE PERMISSÃO
elif pagina == "Lançamentos":
    st.title("📥 Lançamentos do Caixa")
    
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    # Layout responsivo para seleção de mês
    col1, col2 = st.columns([1, 3])
    
    with col1:
        mes_selecionado = st.selectbox("**Selecione o Mês**", meses)
    
    with col2:
        st.info(f"💼 Trabalhando no mês de **{mes_selecionado}**")
        if not user_can_edit():
            st.warning("👀 **Modo de Visualização** - Você pode apenas visualizar os lançamentos.")
    
    # Buscar lançamentos do banco
    df_mes = get_lancamentos_mes(mes_selecionado)
    
    # Apenas usuários com permissão de edição podem adicionar lançamentos
    if user_can_edit():
        st.subheader("➕ Adicionar Lançamento")
        
        # Layout responsivo para o formulário
        with st.form("form_lancamento", clear_on_submit=True):
            col3, col4, col5 = st.columns([2, 2, 1])
            
            with col3:
                data = st.date_input("**Data**", datetime.now().date())
                historico = st.text_input("**Histórico**", placeholder="Descrição do lançamento...")
            
            with col4:
                complemento = st.text_input("**Complemento**", placeholder="Informações adicionais...")
                tipo_movimento = st.selectbox("**Tipo de Movimento**", ["Entrada", "Saída"])
            
            with col5:
                if tipo_movimento == "Entrada":
                    entrada = st.number_input("**Valor (R$)**", min_value=0.0, step=0.01, format="%.2f")
                    saida = 0.0
                else:
                    saida = st.number_input("**Valor (R$)**", min_value=0.0, step=0.01, format="%.2f")
                    entrada = 0.0
            
            submitted = st.form_submit_button("💾 Salvar Lançamento", use_container_width=True)
            
            if submitted and historico:
                # ... (código existente para salvar lançamento)
    else:
        st.info("💡 Para adicionar ou editar lançamentos, solicite permissão de edição ao administrador.")
    
    # Exibir lançamentos do mês (todos os usuários podem visualizar)
    st.subheader(f"📋 Lançamentos - {mes_selecionado}")
    
    if not df_mes.empty:
        # ... (código existente para exibir lançamentos)
        
        # Apenas usuários com permissão de edição podem gerenciar lançamentos
        if user_can_edit():
            # Seção de Edição de Lançamentos
            st.subheader("✏️ Gerenciar Lançamentos")
            
            # ... (código existente para editar/excluir lançamentos)
            
            # Botão para limpar lançamentos do mês (apenas editores)
            if st.button(f"🗑️ Limpar TODOS os Lançamentos de {mes_selecionado}", use_container_width=True, type="secondary"):
                if st.checkbox("✅ Confirmar exclusão de TODOS os lançamentos"):
                    limpar_lancamentos_mes(mes_selecionado)
                    st.rerun()
        else:
            st.info("🔒 A edição de lançamentos está disponível apenas para usuários com permissão de edição.")

# Na página de Gerenciar Usuários (sidebar) - APENAS ADMIN
if st.session_state.permissao == 'admin':
    with st.sidebar.expander("👥 Gerenciar Usuários"):
        st.subheader("Usuários do Sistema")
        
        # Listar usuários existentes
        users = get_all_users()
        if users:
            st.write("**Usuários cadastrados:**")
            for i, (username, permissao, created_at) in enumerate(users, 1):
                st.write(f"{i}. **{username}** - {PERMISSOES.get(permissao, 'Desconhecida')} - Criado em: {created_at[:10]}")
            
            st.markdown("---")
            
            # Editar permissões de usuário
            st.subheader("Editar Permissões")
            user_to_edit = st.selectbox(
                "Selecione o usuário para editar:",
                [user[0] for user in users if user[0] != 'admin']  # Não permitir editar admin
            )
            
            if user_to_edit:
                # Buscar permissão atual do usuário
                permissao_atual = next((user[1] for user in users if user[0] == user_to_edit), 'visualizador')
                
                nova_permissao = st.selectbox(
                    "Nova permissão:",
                    options=list(PERMISSOES.keys()),
                    index=list(PERMISSOES.keys()).index(permissao_atual),
                    format_func=lambda x: PERMISSOES[x]
                )
                
                if st.button("💾 Atualizar Permissão", use_container_width=True):
                    if nova_permissao != permissao_atual:
                        success, message = update_user_permission(user_to_edit, nova_permissao)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            st.markdown("---")
            
            # Excluir usuário
            st.subheader("Excluir Usuário")
            user_to_delete = st.selectbox(
                "Selecione o usuário para excluir:",
                [user[0] for user in users if user[0] != st.session_state.username]
            )
            
            if user_to_delete:
                if st.button("🗑️ Excluir Usuário", use_container_width=True):
                    if st.checkbox("✅ Confirmar exclusão do usuário"):
                        success, message = delete_user(user_to_delete)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info("Nenhum usuário cadastrado.")

# Na página de Ajuda - Adicionar informações sobre permissões
if pagina == "Ajuda":
    # ... (código existente)
    
    st.subheader("🔐 Sistema de Permissões")
    
    col_perm1, col_perm2 = st.columns(2)
    
    with col_perm1:
        st.markdown("""
        **📊 Níveis de Permissão:**
        
        - **👑 Administrador**: Acesso completo a todas as funcionalidades
        - **✏️ Editor**: Pode adicionar, editar e excluir lançamentos e contas
        - **👀 Visualizador**: Apenas visualização de dados e relatórios
        
        **🔒 Recursos por Permissão:**
        """)
    
    with col_perm2:
        st.markdown("""
        **Visualizador pode:**
        - Ver contas existentes
        - Visualizar lançamentos
        - Ver relatórios e gráficos
        - Exportar dados
        - Alterar própria senha
        
        **Editor pode (além do acima):**
        - Adicionar/editar/excluir contas
        - Adicionar/editar/excluir lançamentos
        - Limpar lançamentos do mês
        
        **Admin pode (além de tudo):**
        - Gerenciar usuários
        - Alterar permissões
        - Excluir usuários
        """)

# Inicializar bancos de dados
init_db()
init_auth_db()  # AGORA COM SISTEMA DE PERMISSÕES

# ... (o restante do código permanece igual)
