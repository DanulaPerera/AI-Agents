import streamlit as st
import pyodbc
import pandas as pd
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="BOI Sri Lanka AI Assistant",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for BOI branding
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #F8FAFC;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3B82F6;
    }
    .query-box {
        background: #F1F5F9;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }
    .success-message {
        background: #10B981;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .error-message {
        background: #EF4444;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Database schema
DATABASE_SCHEMA = """ This schema is private and intended solely for the internal use of the Board of Investment (BOI). """



@st.cache_resource
def init_openai_client():
    """Initialize OpenAI client"""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    )

@st.cache_resource
def init_database_connection():
    """Initialize database connection"""
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=xx.xx.xx.xx;"
            "DATABASE=xxxxx;"
            "UID=xxxxx;"
            "PWD=xxxxx;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def generate_sql_query(question, client):
    """Convert natural language to SQL using AI"""
    prompt = f"""You are an expert SQL Server assistant for BOI Sri Lanka (Board of Investment). 
Convert the following natural language question into a SQL Server query for investment project data.

{DATABASE_SCHEMA}

IMPORTANT RULES:

This Data is private and intended solely for the internal use of the Board of Investment (BOI).

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
        st.error(f"Error calling AI API: {e}")
        return None

def execute_query(sql_query, conn):
    """Execute SQL query and return results"""
    try:
        df = pd.read_sql(sql_query, conn)
        return df, None
    except Exception as e:
        return None, str(e)

def create_visualizations(df):
    """Create visualizations based on the data"""
    if df is None or df.empty:
        return
    
    # Check for common financial columns
    financial_cols = [col for col in df.columns if any(keyword in col.upper() for keyword in 
                     ['INVESTMENT', 'EXPORT', 'VALUE', 'AMOUNT', 'EQUITY', 'LOAN'])]
    
    date_cols = [col for col in df.columns if any(keyword in col.upper() for keyword in 
                ['DATE', 'YEAR'])]
    
    # Create visualizations if we have appropriate data
    if financial_cols and len(df) > 1:
        st.subheader("📊 Data Visualizations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if len(financial_cols) >= 1:
                # Bar chart for financial data
                fig = px.bar(df.head(20), y=df.columns[0], x=financial_cols[0], 
                           title=f"{financial_cols[0]} by {df.columns[0]}")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if len(financial_cols) >= 2:
                # Scatter plot for two financial columns
                fig = px.scatter(df, x=financial_cols[0], y=financial_cols[1],
                               title=f"{financial_cols[1]} vs {financial_cols[0]}")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🇱🇰 BOI Sri Lanka AI Investment Assistant</h1>
        <p>Intelligent Database Query System for Investment Project Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize connections
    client = init_openai_client()
    conn = init_database_connection()
    
    if conn is None:
        st.error("❌ Cannot connect to database. Please check connection settings.")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Query Assistant")
        
        st.markdown("### 💡 Example Questions:")
        example_questions = [
            "Show all investment projects",
            "List approved projects",
            "Projects in IT sector", 
            "Export performance for 2023",
            "Foreign investment statistics",
            "Employment data by project",
            "Top 10 projects by investment amount",
            "Projects by investor country"
        ]
        
        for question in example_questions:
            if st.button(question, key=f"example_{question}"):
                st.session_state.user_question = question
        
        st.markdown("---")
        st.markdown("### 📊 Database Info")
        st.info("""
        **Main Tables:**
        - General_Project_Detail
        - ShareHolders_Country  
        - ANNUAT2024 (Performance Data)
        
        **Key Metrics:**
        - Investment amounts
        - Export performance
        - Employment data
        - Project approvals
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Ask Your Question")
        
        # Get user question
        user_question = st.text_input(
            "Enter your question about BOI investment data:",
            value=st.session_state.get('user_question', ''),
            placeholder="e.g., Show me all approved projects in the IT sector"
        )
        
        col_query, col_clear = st.columns([1, 1])
        with col_query:
            query_button = st.button("🔍 Generate & Execute Query", type="primary")
        with col_clear:
            if st.button("🗑️ Clear"):
                st.session_state.user_question = ""
                st.rerun()
    
    with col2:
        st.subheader("📈 Quick Stats")
        
        # Get some quick stats
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM General_Project_Detail")
            total_projects = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT NewSector) FROM General_Project_Detail WHERE NewSector IS NOT NULL")
            total_sectors = cursor.fetchone()[0]


            
            st.metric("Total Projects", f"{total_projects:,}")
            st.metric("Active Sectors", f"{total_sectors}")
            
        except Exception as e:
            st.warning("Could not load quick stats")
    
    # Process query
    if query_button and user_question:
        with st.spinner("🤖 AI is analyzing your question..."):
            # Generate SQL query
            sql_query = generate_sql_query(user_question, client)
            
            if sql_query:
                st.subheader("🔍 Generated SQL Query")
                st.markdown('<div class="query-box">', unsafe_allow_html=True)
                st.code(sql_query, language="sql")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Execute query
                with st.spinner("📊 Executing query..."):
                    df, error = execute_query(sql_query, conn)
                    
                    if error:
                        st.markdown('<div class="error-message">', unsafe_allow_html=True)
                        st.error(f"❌ Query Error: {error}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="success-message">', unsafe_allow_html=True)
                        st.success(f"✅ Query executed successfully! Found {len(df)} results.")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        if not df.empty:
                            # Show results
                            st.subheader("📋 Results")
                            
                            # Add download button
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results as CSV",
                                data=csv,
                                file_name=f"boi_query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                            
                            # Display data
                            st.dataframe(df, use_container_width=True, height=400)
                            
                            # Show summary statistics for numerical columns
                            numeric_cols = df.select_dtypes(include=['number']).columns
                            if len(numeric_cols) > 0:
                                st.subheader("📊 Summary Statistics")
                                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                            
                            # Create visualizations
                            create_visualizations(df)
                        else:
                            st.info("No results found for your query.")
            else:
                st.error("❌ Failed to generate SQL query. Please try rephrasing your question.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #64748B;'>
        <p>🇱🇰 BOI Sri Lanka AI Investment Assistant | Powered by dyrexx.ai</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    # Initialize session state
    if 'user_question' not in st.session_state:
        st.session_state.user_question = ""
    
    main()
