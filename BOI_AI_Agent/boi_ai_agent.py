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
DATABASE_SCHEMA = """
BOI Sri Lanka Investment Database Schema (cdsd):

## Core Tables

### 1. General_Project_Detail - Main project information repository
**Purpose**: Contains comprehensive project details, investment amounts, employment data, and status tracking

**Key Fields**:
- Reference_Number: Unique project identifier (Primary Key)
- Project_Type: Type classification of the project
- Project_Category: Category classification (21=Sec.17, 24=Non BOI, 61-64=Sec.16, 71-74=Sec.17)
- Project_Name: Official name of the investment project
- Enterprise_Code: Business enterprise identifier
- Project_Status: Current status (see Project_Status codes below)
- Project_Officer_Code: Assigned BOI officer identifier
- Product_Description: Description of products/services
- Contact_Person: Primary contact for the project
- Registration_Number: Official registration number

**Important Dates**:
- Application_Submitted_Date: When application was submitted
- Board_Approval_Date: Date of board approval
- Approval_Date: Official approval date
- Agreement_Date: Agreement signing date
- Implementation_Date: Project implementation start
- Commercial_Operation_Date: Commercial operations start

**Investment & Employment Data**:
- Est_Total_Investment_For: Estimated foreign investment amount
- Est_Total_Investment_Loc: Estimated local investment amount
- Est_Total_Manpower_For: Estimated foreign employment count
- Est_Total_Manpower_Loc: Estimated local employment count

**Classification Codes**:
- ISIC_Code: International Standard Industrial Classification
- NewSector: Sector classification (IT, Manufacturing, Services, etc.)
- GICS: Global Industry Classification Standard
- ExpPct: Export percentage
- LocPct: Local percentage

### 2. ShareHolders_Country - Shareholder and investor information
**Purpose**: Tracks shareholder details and country origins for investment analysis

**Key Fields**:
- Reference_Number: Links to General_Project_Detail (Foreign Key)
- Project_Type, Project_Category: Project classification
- Share_Holder_Name1-15: Up to 15 shareholder names
- Country_Code1-15: Corresponding country codes (see Country Codes reference)
- ShareHolder_Type: Type of shareholder
- Investor_Number1-15: Investor identification numbers

### 3. ANNUAT2024 - Annual performance tracking
**Purpose**: Time-series data for project performance, exports, employment, and investments

**Key Fields**:
- REFNO: Reference number linking to General_Project_Detail (Foreign Key)
- PRJTYPE, PRJCAT: Project type and category
- YEAR: Reporting year
- EXPVLUANU: Annual export value (in currency units)
- EMPVLUANU: Annual employment figures (number of employees)
- RMIMPANU: Raw material imports annually (in currency units)
- LOCINVANU: Local investment annually (in currency units)
- FORINVANU: Foreign investment annually (in currency units)
- FOREQTYANU: Foreign equity annually (in currency units)
- LOCEQTYANU: Local equity annually (in currency units)

## Project Status Codes (Active/Inactive Classification)

**ACTIVE PROJECTS** (Currently operational or progressing):
- A1: Awaiting Approval
- B1: Approved/Awaiting Agreement
- C1: Awaiting Implementation
- C2: Commenced Implementation
- C3: Under Construction
- D1: Awaiting Commercial Operation
- D2: Partially Commenced Commercial Operations
- E1: In Commercial Operation

**PIPELINE PROJECTS** (Currently Active, But not In commercial):
- A1: Awaiting Approval
- B1: Approved/Awaiting Agreement
- C1: Awaiting Implementation
- C2: Commenced Implementation
- C3: Under Construction
- D1: Awaiting Commercial Operation
- D2: Partially Commenced Commercial Operations

**INACTIVE PROJECTS** (Closed, cancelled, or dormant):
- A0: Rejected Applications
- B0: Dormant
- C4: Implementation Ceased
- F1: Operation Suspended
- G1-G9: Approval Withdrawn (various reasons)
- H1-H9: Agreement Cancelled (various reasons)
- I1: Closed

**NEW PROJECTS** ():
- Project_Status = "GENN"

**EXPANSION PROJECTS** ():
- Project_Status != "GENN"

## Project Categories
- 21: Section 17
- 24: Non BOI Companies
- 61-64: Section 16
- 71-72, 74: Section 17

## Key Country Codes (Most relevant for Sri Lanka) - [@country_code]

- AF: Afghanistan
- AL: Albania
- DZ: Algeria
- AS: American Samoa
- AD: Andorra
- AO: Angola
- AI: Anguilla
- AQ: Antarctica
- AG: Antigua & Barbuda
- AR: Argentina
- AM: Armenia
- AW: Aruba
- AU: Australia
- AT: Austria
- AZ: Azerbaijan
- BS: Bahamas
- BH: Bahrain
- BD: Bangladesh
- BB: Barbados
- BY: Belarus
- BE: Belgium
- BZ: Belize
- BJ: Benin
- BM: Bermuda
- BT: Bhutan
- BO: Bolivia
- BA: Bosnia & Herzegovina
- BW: Botswana
- BV: Bouvet Island
- BR: Brazil
- IO: British Indian Ocean
- BN: Brunei Darussalam
- BG: Bulgaria
- BF: Burkina Faso
- BI: Burundi
- KH: Cambodia
- CM: Cameroon
- CA: Canada
- CV: Cape Verde
- KY: Cayman Islands
- CF: Central African Republic
- TD: Chad
- CD: Channel Islands
- CL: Chile
- CN: China
- CX: Christmas Island
- CC: Cocos (Keeling) Islands
- CO: Colombia
- KM: Comoros
- CG: Congo
- CK: Cook Islands
- CR: Costa Rica
- CI: Cote D'ivoire
- CY: Cyprus
- CU: Cuba
- CZ: Czech Republic
- DE: Germany, Federal Republic of
- CS: Czechoslovakia
- YD: Democratic Yemen
- DK: Denmark
- DJ: Djibouti
- DM: Dominica
- DO: Dominican Republic
- DB: Dubai
- TP: East Timor
- EC: Ecuador
- EG: Egypt
- EI: Eire
- SV: El Salvador
- GO: Equatorial Guinea
- EA: Eritrea
- EE: Estonia
- ET: Ethiopia
- EU: European Union
- FK: Falkland Islands (Malvinas)
- FO: Faroe Islands
- FJ: Fiji
- ES: Spain
- FI: Finland
- GF: French Guiana
- PF: French Polynesia
- GA: Gabon
- GM: Gambia
- GG: Georgia
- FR: France
- GH: Ghana
- GI: Gibraltar
- GR: Greece
- GL: Greenland
- GD: Grenada
- GP: Guadeloupe
- GU: Guam
- GT: Guatemala
- GN: Guinea
- GW: Guinea-Bussau
- GY: Guyana
- HT: Haiti
- HM: Heard And Mc Donald
- HN: Honduras
- HK: Hong Kong
- HR: Croatia
- IS: Iceland
- IN: India
- ID: Indonesia
- IR: Iran (Islamic Republic)
- IQ: Iraq
- HU: Hungary
- IM: Isle Of Man
- IL: Israel
- IE: Ireland
- IC: Ivory Coast
- JM: Jamaica
- JP: Japan
- JT: Johnston Island
- JO: Jordan
- KZ: Kazakstan
- KE: Kenya
- KI: Kiribati
- KP: Korea, Democratic Peoples Rep.
- KR: Korea, Republic Of (South Korea)
- KW: Kuwait
- KG: Kyrgyzatan
- LA: Lao People's Democratic Republic
- IT: Italy
- LB: Lebanon
- LS: Lesotho
- LR: Liberia
- LI: Lichtenstein
- LT: Lithuania
- LU: Luxembourg
- LY: Lybian Arab Jamahiri
- MO: Macau
- MK: Macedonia
- MG: Madagascar
- MW: Malawi
- MY: Malaysia
- MV: Maldives
- ML: Mali
- LV: Latvia
- MH: Marshall Islands
- MQ: Martinique
- MR: Mauritania
- MU: Mauritius
- MX: Mexico
- FM: Micronesia, Federated States Of
- MI: Midway Islands
- MC: Monaco
- MN: Mongolia
- MS: Montserrat
- MA: Morocco
- MZ: Mozambique
- MM: Myanmar
- NA: Namibia
- NR: Nauru
- NP: Nepal
- MT: Malta
- AN: Netherlands Antilles
- NT: Neutral Zone
- NC: New Caledonia
- NZ: New Zealand
- NI: Nicaragua
- NE: Niger
- NG: Nigeria
- NU: Niue
- NF: Norfolk Island
- MP: Northern Mariana Island
- NO: Norway
- 0: Not defined
- OM: Oman
- OF: Other Foreign
- PK: Pakistan
- PW: Palau
- PA: Panama
- PG: Papua New Guinea
- PY: Paraguay
- PE: Peru
- PR: Peurto Rico
- PH: Philippines
- PN: Pitcairn
- NL: Netherlands
- PL: Poland
- TF: Prench Southern Terr
- QA: Qatar
- MD: Republic of Moldova
- RE: Reunion
- PT: Portugal
- RS: Russia
- RW: Rwanda
- WS: Samoa
- SM: San Marino
- ST: Sao Tome And Principe
- SA: Saudi Arabia
- SN: Senegal
- RU: Serbia
- SC: Seychelles
- SL: Sierra Leone
- SG: Singapore
- RO: Romania
- SE: Sweden
- SB: Solomon Islands
- SO: Somalia
- ZA: South Africa
- SI: Slovenia
- LK: Sri Lanka (domestic investors)
- LC: St Lucia
- SH: St. Helena
- KN: St. Kitts And Nevis
- PM: St. Pierre Et Miquel
- VC: St. Vincent And The Grenadines
- PS: State of Palestine
- SD: Sudan
- SR: Surinam
- SJ: Svalbard And Jan Mayen Islands
- SZ: Swaziland
- SK: Slovakia
- CH: Switzerland
- SY: Syrian Arab Republic
- TW: Taiwan, Province Of China
- TJ: Tajikistan
- TZ: Tanzania
- TH: Thailand
- TG: Togo
- TK: Tokelau
- TO: Tonga
- TT: Trinidad And Tobago
- TN: Tunisia
- TR: Turkey
- TM: Turkmenistan
- TC: Turks And Caicos Islands
- TV: Tuvalu
- UM: U.S. Minor Outlying
- UG: Uganda
- UA: Ukrainian Ssr
- AE: United Arab Emirates
- GB: United Kingdom
- US: United States
- UY: Uruguay
- SU: USSR
- UZ: Uzbekistan
- VU: Vanuatu
- VA: Vatican City State (
- VE: Venezuela
- VN: Vietnam
- VG: Virgin Islands (British)
- VI: Virgin Islands (Us)
- X1: W.Africa
- WF: Wallis & Futuna Isla
- WI: West Indies
- WB: West Indies (British)
- EH: Western Sahara
- YE: Yemen
- YU: Yugoslavia
- ZR: Zaire
- ZM: Zambia
- ZW: Zimbabwe


## Query Guidelines for AI Assistant

*RELATIONSHIPS for tables*
- ShareHolders_Country.Reference_Number → General_Project_Detail.Reference_Number
- ShareHolders_Country.Project_Type → General_Project_Detail.Project_Type
- ShareHolders_Country.Project_Category → General_Project_Detail.Project_Category
- ANNUAT2024.REFNO → General_Project_Detail.Reference_Number
- ANNUAT2024.PRJTYPE → General_Project_Detail.Project_Type
- ANNUAT2024.PRJCAT → General_Project_Detail.Project_Category

**Common Query Patterns**:

1. **Active Projects**: WHERE Project_Status IN ('A1','B1','C1','C2','C3','D1','D2','E1')
2. **Investment Analysis**: SUM(EXPVLUANU)
3. **Employment Analysis**: SUM(EMPVLUANU)
4. **Sector Analysis**: GROUP BY NewSector
5. **Country Analysis**: JOIN with ShareHolders_Country, GROUP BY Country_Code1-15
6. **Time Series**: JOIN with ANNUAT2024, GROUP BY YEAR
7. **Export Performance**: SUM(EXPVLUANU) from ANNUAT2024 table

**Financial Data Interpretation**:
- Investment amounts are in local currency (LKR) or foreign currency (USD)
- ANNUAT2024 table contains actual performance data (annual figures)
- General_Project_Detail contains estimated/projected figures
- Use ANNUAT2024 for historical analysis, General_Project_Detail for current status

**Important Notes**:

- ALWAYS USE LEFT OUTER JOIN - This is mandatory for all queries
- Use SQL Server syntax (square brackets for reserved words)
- Main identifier is Reference_Number (may have leading zeros)
- Date fields may contain NULL values for future milestones
- Country codes follow ISO standards but include some custom codes
- Project categories determine regulatory framework and incentives

## AI Custom Report: COUNTRY REPORT LOGIC

**Trigger Phrase**: "Country Report for [Country_Name]" or "Project list for [Country_Name]"

**Expected Output**: A detailed project-level table filtered by investor country, including the following columns:
- Section (Project_Category)- Remember To decode it
- Project_Name
- Product_Description
- NewSector
- Current Status (Project_Status)

Apply the following filters:
- Project_Status IN ('A1','B1','C1','C2','C3','D1','D2','E1')
- Project_Type_N = "GENN"

Decode the Current Status (Project_Status)
- A1: Awaiting Approval
- B1: Approved/Awaiting Agreement
- C1: Awaiting Implementation
- C2: Commenced Implementation
- C3: Under Construction
- D1: Awaiting Commercial Operation
- D2: Partially Commenced Commercial Operations
- E1: In Commercial Operation

**Data Source**:
- `General_Project_Detail` (main project metadata)
- Joined with `ShareHolders_Country` (to match Country_Code1 through Country_Code15)

**Country Matching Logic**:
- WHERE [Country_Code1] = 'XX' OR [Country_Code2] = 'XX' OR ... [Country_Code15] = 'XX'
- Country codes match ISO format or the custom country code list provided in schema

**Project Status Filtering**:
- Default: No status filter (all projects)
- Optional: If user specifies:
  - "active projects": filter by Project_Status IN ('A1','B1','C1','C2','C3','D1','D2','E1')
  - "pipeline projects": filter by Project_Status IN ('A1','B1','C1','C2','C3','D1','D2')

**Project Type Classification**:
- Section is derived from Project_Category:
  - 21 = Section 17
  - 24 = Non BOI
  - 61–64 = Section 16
  - 71–74 = Section 17

**Sorting**:
- Default: Sort by Project_Status ascending, then Project_Name

**Example Query Logic** (pseudo-SQL for AI generation):
```sql
SELECT * FROM
    General_Project_Detail g
JOIN 
    ShareHolders_Country s ON 
        g.Reference_Number = s.Reference_Number AND 
        g.Project_Type = s.Project_Type AND 
        g.Project_Category = s.Project_Category
WHERE 
    'XX' IN (
        s.Country_Code1, s.Country_Code2, s.Country_Code3, s.Country_Code4, s.Country_Code5,
        s.Country_Code6, s.Country_Code7, s.Country_Code8, s.Country_Code9, s.Country_Code10,
        s.Country_Code11, s.Country_Code12, s.Country_Code13, s.Country_Code14, s.Country_Code15
    )
    AND g.Project_Status IN ('A1','B1','C1','C2','C3','D1','D2','E1') AND Project_Category_N != 24 AND Project_Type_N = 'GENN'
    ORDER BY 
    g.Project_Status, g.Project_Name;


## AI Custom Report: SUMMARY REPORT LOGIC (CORRECTED)
**Trigger Phrase**: "Summary Report for [Country_Name]"

-- Complete SQL Query for Summary Report
WITH BaseData AS (
    SELECT DISTINCT
        G.Reference_Number_N,
        G.Project_Type_N,
        G.Project_Category_N,
        G.NewSector,
        G.Project_Status,
        S.ShareHolder_Type,
        CASE
            WHEN G.Project_Category_N IN (61,62,63,64) THEN 'Section 16'
            WHEN G.Project_Category_N IN (21,71,72,74) THEN 'Section 17'
            ELSE 'Other'
        END AS Section,
        CASE WHEN '@country_code' IN (
            S.Country_Code1, S.Country_Code2, S.Country_Code3, S.Country_Code4,
            S.Country_Code5, S.Country_Code6, S.Country_Code7, S.Country_Code8,
            S.Country_Code9, S.Country_Code10, S.Country_Code11, S.Country_Code12,
            S.Country_Code13, S.Country_Code14, S.Country_Code15
        ) THEN 1 ELSE 0 END AS Has_Country
    FROM General_Project_Detail G
    LEFT JOIN ShareHolders_Country S ON
        G.Reference_Number = S.Reference_Number AND
        G.Project_Type = S.Project_Type AND
        G.Project_Category = S.Project_Category
    WHERE
        G.Project_Category_N != 24
        AND G.Project_Status IN ('A1','B1','C1','C2','C3','D1','D2','E1')
        AND G.Project_Type_N = 'GENN'
        AND '@country_code' IN (
            S.Country_Code1, S.Country_Code2, S.Country_Code3, S.Country_Code4,
            S.Country_Code5, S.Country_Code6, S.Country_Code7, S.Country_Code8,
            S.Country_Code9, S.Country_Code10, S.Country_Code11, S.Country_Code12,
            S.Country_Code13, S.Country_Code14, S.Country_Code15
        )
),

ExportsEmployment AS (
    SELECT
        CASE
            WHEN G.Project_Category_N IN (61,62,63,64) THEN 'Section 16'
            WHEN G.Project_Category_N IN (21,71,72,74) THEN 'Section 17'
            ELSE 'Other'
        END AS Section,
        SUM(A.EXPVLUANU) AS Exports_2024 in USD Mn,
        SUM(A.EMPVLUANU) AS Employment_2024
    FROM Annuat2024 A
    left outer JOIN General_Project_Detail G ON
        A.REFNO = G.Reference_Number AND
        A.PRJTYPE = G.Project_Type AND
        A.PRJCAT = G.Project_Category
    left outer JOIN ShareHolders_Country S ON
        G.Reference_Number = S.Reference_Number AND
        G.Project_Type = S.Project_Type AND
        G.Project_Category = S.Project_Category
    WHERE       
        G.Project_Category_N != 24
        AND '@country_code' IN (
            S.Country_Code1, S.Country_Code2, S.Country_Code3, S.Country_Code4,
            S.Country_Code5, S.Country_Code6, S.Country_Code7, S.Country_Code8,
            S.Country_Code9, S.Country_Code10, S.Country_Code11, S.Country_Code12,
            S.Country_Code13, S.Country_Code14, S.Country_Code15
        )
        
    GROUP BY
        CASE
            WHEN G.Project_Category_N IN (61,62,63,64) THEN 'Section 16'
            WHEN G.Project_Category_N IN (21,71,72,74) THEN 'Section 17'
            ELSE 'Other'
        END
),

CombinedMetrics AS (
    SELECT
        Section,
        COUNT(DISTINCT Reference_Number_N) AS Total_Projects,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' THEN Reference_Number_N END) AS Commercial_Projects,
        COUNT(DISTINCT CASE WHEN Project_Status IN ('A1','B1','C1','C2','C3','D1','D2') THEN Reference_Number_N END) AS Pipeline_Projects,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Manufacturing' THEN Reference_Number_N END) AS Manufacturing,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Apparel' THEN Reference_Number_N END) AS Apparel,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Infrastructure' THEN Reference_Number_N END) AS Infrastructure,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Knowledge Services' THEN Reference_Number_N END) AS Knowledge_Services,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Tourism & Leisure' THEN Reference_Number_N END) AS Tourism_Leisure,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Utilities' THEN Reference_Number_N END) AS Utilities,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Services' THEN Reference_Number_N END) AS Services,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND NewSector = 'Agriculture' THEN Reference_Number_N END) AS Agriculture,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND ShareHolder_Type = 'Foreign' THEN Reference_Number_N END) AS Foreign_Only,
        COUNT(DISTINCT CASE WHEN Project_Status = 'E1' AND ShareHolder_Type = 'Joint Venture' THEN Reference_Number_N END) AS Joint_Venture
    FROM BaseData
    WHERE Has_Country = 1
    GROUP BY Section
)

SELECT
    COALESCE(cm.Section, EM.Section) AS Section,
    ISNULL(cm.Total_Projects, 0) AS Total_Projects,
    ISNULL(cm.Commercial_Projects, 0) AS Commercial_Projects,
    ISNULL(cm.Pipeline_Projects, 0) AS Pipeline_Projects,
    ISNULL(cm.Foreign_Only, 0) AS Foreign_Only,
    ISNULL(cm.Joint_Venture, 0) AS Joint_Venture,
    ISNULL(cm.Manufacturing, 0) AS Manufacturing,
    ISNULL(cm.Apparel, 0) AS Apparel,
    ISNULL(cm.Infrastructure, 0) AS Infrastructure,
    ISNULL(cm.Knowledge_Services, 0) AS Knowledge_Services,
    ISNULL(cm.Tourism_Leisure, 0) AS Tourism_Leisure,
    ISNULL(cm.Utilities, 0) AS Utilities,
    ISNULL(cm.Services, 0) AS Services,
    ISNULL(cm.Agriculture, 0) AS Agriculture,
    ISNULL(EM.Exports_2024, 0) AS Exports_2024,
    ISNULL(EM.Employment_2024, 0) AS Employment_2024
FROM CombinedMetrics cm
FULL OUTER JOIN ExportsEmployment EM ON cm.Section = EM.Section
ORDER BY Section;

"""

@st.cache_resource
def init_openai_client():
    """Initialize OpenAI client"""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )

@st.cache_resource
def init_database_connection():
    """Initialize database connection"""
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=10.0.2.20;"
            "DATABASE=cdsd;"
            "UID=rptgen;"
            "PWD=rptgn;"
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
1. Use SQL Server syntax (no MySQL backticks)
2. Use square brackets [ ] for reserved words if needed
3. Use proper JOINs when querying multiple tables
4. Use GETDATE() for current date/time
5. Return ONLY the SQL query, nothing else
6. For date comparisons, use proper SQL Server date functions
7. Consider BOI business context (investments, exports, employment, project approvals)
8. Main table is General_Project_Detail with composite key (Reference_Number, Project_Type, Project_Category)
9. For performance data, JOIN with ANNUAT2024 table
10. For investor information, JOIN with ShareHolders_Country table
11. Use appropriate WHERE clauses for project status, dates, sectors
12. When showing financial data, consider both foreign (FORINVANU) and local (LOCINVANU) investments
13. All the Projects that we called as "New" is to be where Project_Status = "GENN"
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