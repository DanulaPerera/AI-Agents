import streamlit as st
import pyodbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
import json
from datetime import datetime, timedelta
import io

# Page configuration
st.set_page_config(
    page_title="Library Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .sql-code {
        background-color: #2d3748;
        color: #e2e8f0;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False

# Database configuration
@st.cache_resource
def init_database():
    """Initialize database connection"""
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost\\SQLEXPRESS;"
            "DATABASE=LibraryManagementDB;"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

@st.cache_resource
def init_openai():
    """Initialize OpenAI client"""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # Replace with your key
    )

# Database schema
DATABASE_SCHEMA = """
DATABASE SCHEMA - LibraryManagementDB:

1. Authors(AuthorID, FirstName, LastName, BirthDate, Nationality, Email, CreatedDate)
2. Categories(CategoryID, CategoryName, Description, CreatedDate)  
3. Books(BookID, Title, ISBN, AuthorID, CategoryID, PublicationYear, Publisher, TotalCopies, AvailableCopies, Price, CreatedDate)
4. Members(MemberID, FirstName, LastName, Email, Phone, Address, JoinDate, MembershipType, IsActive, CreatedDate)
5. BorrowingRecords(RecordID, MemberID, BookID, BorrowDate, DueDate, ReturnDate, Fine, Status, CreatedDate)

RELATIONSHIPS:
- Books.AuthorID → Authors.AuthorID
- Books.CategoryID → Categories.CategoryID  
- BorrowingRecords.MemberID → Members.MemberID
- BorrowingRecords.BookID → Books.BookID
"""

def generate_sql_query(question, client):
    """Generate SQL query from natural language"""
    prompt = f"""You are an expert SQL Server assistant for library management analytics.
    Convert the following question into a SQL Server query.

    {DATABASE_SCHEMA}

    IMPORTANT RULES:
    1. Use SQL Server syntax
    2. Use proper JOINs when needed
    3. Use GETDATE() for current date
    4. Return ONLY the SQL query
    5. Focus on analytics and insights for directors/policy makers

    Question: {question}

    SQL Query:"""

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat:free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        sql_query = response.choices[0].message.content.strip()
        # Clean up the response
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        
        return sql_query.strip()
    except Exception as e:
        st.error(f"Error generating SQL: {e}")
        return None

def execute_query(conn, query):
    """Execute SQL query and return results"""
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            df = pd.DataFrame.from_records(rows, columns=columns)
            cursor.close()
            return df, None
        else:
            conn.commit()
            cursor.close()
            return None, "Query executed successfully"
            
    except Exception as e:
        return None, f"Error: {e}"

def create_visualization(df, query_text):
    """Create appropriate visualization based on data"""
    if df is None or df.empty:
        return None
    
    # Simple heuristics for chart type selection
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
        # Bar chart
        fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], 
                     title=f"Analysis: {query_text[:50]}...")
        return fig
    elif len(numeric_cols) >= 2:
        # Scatter plot
        fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1],
                        title=f"Analysis: {query_text[:50]}...")
        return fig
    
    return None

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x100/1f77b4/white?text=Library+AI", width=200)
    st.title("🤖 Library Analytics AI")
    
    # Connection status
    conn = init_database()
    if conn:
        st.success("🟢 Database Connected")
        st.session_state.db_connected = True
    else:
        st.error("🔴 Database Disconnected")
        st.session_state.db_connected = False
    
    st.markdown("---")
    
    # Quick Analytics Buttons
    st.subheader("📊 Quick Analytics")
    
    quick_queries = {
        "📚 Total Books": "SELECT COUNT(*) as TotalBooks FROM Books",
        "👥 Active Members": "SELECT COUNT(*) as ActiveMembers FROM Members WHERE IsActive = 1",
        "📖 Currently Borrowed": "SELECT COUNT(*) as BorrowedBooks FROM BorrowingRecords WHERE Status = 'Borrowed'",
        "⚠️ Overdue Books": "SELECT COUNT(*) as OverdueBooks FROM BorrowingRecords WHERE Status = 'Overdue'",
        "💰 Total Fines": "SELECT SUM(Fine) as TotalFines FROM BorrowingRecords WHERE Fine > 0"
    }
    
    for label, query in quick_queries.items():
        if st.button(label, key=f"quick_{label}"):
            if st.session_state.db_connected:
                df, error = execute_query(conn, query)
                if df is not None and not df.empty:
                    value = df.iloc[0, 0]
                    st.metric(label, value)
    
    st.markdown("---")
    
    # Sample Questions
    st.subheader("💡 Sample Questions")
    sample_questions = [
        "Show me monthly borrowing trends",
        "Which books are most popular?",
        "What's the average fine amount?",
        "Show member demographics",
        "List overdue books with member details"
    ]
    
    for question in sample_questions:
        if st.button(f"💬 {question}", key=f"sample_{question}"):
            st.session_state.current_question = question

# Main Content
st.markdown('<h1 class="main-header">📊 Library Management Analytics Dashboard</h1>', unsafe_allow_html=True)

# Dashboard Overview
if st.session_state.db_connected:
    col1, col2, col3, col4 = st.columns(4)
    
    # Quick metrics
    with col1:
        df, _ = execute_query(conn, "SELECT COUNT(*) as count FROM Books")
        total_books = df.iloc[0, 0] if df is not None else 0
        st.metric("📚 Total Books", total_books)
    
    with col2:
        df, _ = execute_query(conn, "SELECT COUNT(*) as count FROM Members WHERE IsActive = 1")
        active_members = df.iloc[0, 0] if df is not None else 0
        st.metric("👥 Active Members", active_members)
    
    with col3:
        df, _ = execute_query(conn, "SELECT COUNT(*) as count FROM BorrowingRecords WHERE Status = 'Borrowed'")
        borrowed = df.iloc[0, 0] if df is not None else 0
        st.metric("📖 Currently Borrowed", borrowed)
    
    with col4:
        df, _ = execute_query(conn, "SELECT SUM(Fine) as total FROM BorrowingRecords WHERE Fine > 0")
        total_fines = df.iloc[0, 0] if df is not None and df.iloc[0, 0] is not None else 0
        st.metric("💰 Total Fines", f"${total_fines:.2f}")

# Chat Interface
st.markdown("---")
st.subheader("💬 Ask Questions About Your Library Data")

# Initialize OpenAI client
client = init_openai()

# Chat input
user_question = st.text_input(
    "Ask a question about your library data:",
    placeholder="e.g., Show me the most borrowed books this month",
    key="user_input"
)

if hasattr(st.session_state, 'current_question'):
    user_question = st.session_state.current_question
    delattr(st.session_state, 'current_question')

if user_question and st.session_state.db_connected:
    # Add user message to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_question,
        "timestamp": datetime.now()
    })
    
    with st.spinner("🤖 Analyzing your question..."):
        # Generate SQL query
        sql_query = generate_sql_query(user_question, client)
        
        if sql_query:
            # Execute query
            df, error = execute_query(conn, sql_query)
            
            # Add assistant response to chat history
            if df is not None:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Here's the analysis for: {user_question}",
                    "sql_query": sql_query,
                    "data": df,
                    "timestamp": datetime.now()
                })
            else:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Error: {error}",
                    "sql_query": sql_query,
                    "timestamp": datetime.now()
                })

# Display chat history
if st.session_state.chat_history:
    st.markdown("### 💬 Conversation History")
    
    for i, message in enumerate(reversed(st.session_state.chat_history[-10:])):  # Show last 10 messages
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You:</strong> {message["content"]}<br>
                <small>🕒 {message["timestamp"].strftime("%H:%M:%S")}</small>
            </div>
            """, unsafe_allow_html=True)
        
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 AI Assistant:</strong> {message["content"]}<br>
                <small>🕒 {message["timestamp"].strftime("%H:%M:%S")}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Show SQL query
            if "sql_query" in message:
                with st.expander("🔍 View Generated SQL Query"):
                    st.code(message["sql_query"], language="sql")
            
            # Show data and visualization
            if "data" in message and message["data"] is not None:
                df = message["data"]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.dataframe(df, use_container_width=True)
                
                with col2:
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"library_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                # Create visualization
                fig = create_visualization(df, message.get("content", ""))
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")

# Clear chat button
if st.session_state.chat_history:
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>📊 Library Analytics Dashboard | Powered by AI & SQL Server</p>
</div>
""", unsafe_allow_html=True)
