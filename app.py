import streamlit as st
import pandas as pd
import pg8000
import plotly.express as px
from openai import OpenAI
import PyPDF2

# Function to read and extract text from PDF schema
def extract_schema(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    schema_text = ""
    for page in reader.pages:
        schema_text += page.extract_text()
    return schema_text

# Function to translate natural language to SQL
def nl_to_sql(schema, nl_query, openrouter_api_key):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key,
    )

    prompt = f"""
    Given the database schema described belowand taking into consideration 2 data schemas: raw_business_data and raw_telematics_data and tables and atributes in those data schemas, translate the following natural language query into SQL-query. Respond with SQL code ONLY, DO NOT PROVIDE ADDITIONAL INFORMATION, WORDS, SYMBOLS OR FORMATTING:
    Database description with 2 data schemas:
    {schema}
    Natural Language Query:
    """ + nl_query

    response = client.chat.completions.create(
        extra_headers={},
        extra_body={},
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5000,
        temperature=0
    )

    sql_query = response.choices[0].message.content.strip()
    return sql_query

# Database connection function
def connect_to_db(host, dbname, user, password, port):
    try:
        conn = pg8000.connect(host=host, database=dbname, user=user, password=password, port=int(port))
        return conn
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

# UI for database connection
st.title("PTL Database Explorer based on AI")

with st.sidebar:
    st.header("Database Connection")
    host = st.text_input("Host", value="hostname")
    dbname = st.text_input("Database Name", value="client_XXXXXXX")
    user = st.text_input("Username", value="client_XXXXXXX_user")
    password = st.text_input("Password", type="password")
    port = st.text_input("Port", value="5432")
    openrouter_api_key = st.text_input("OpenRouter API Key", type="password")
    pdf_schema = st.file_uploader("Upload Schema PDF", type=['pdf'])

    connect_button = st.button("Connect")

    if connect_button:
        conn = connect_to_db(host, dbname, user, password, port)
        if conn:
            st.session_state["conn"] = conn
            st.success("Connection established successfully!")
        else:
            st.session_state["conn"] = None

    conn = st.session_state.get("conn", None)
    if conn:
        st.success("Status: Connected")
    else:
        st.warning("Status: Not connected")

# Main content: Natural Language query to SQL
if "conn" in st.session_state and st.session_state["conn"]:
    conn = st.session_state["conn"]

    if pdf_schema and openrouter_api_key:
        schema_text = extract_schema(pdf_schema)
        st.subheader("What would you like to analyse?")
        nl_query = st.text_area("Enter your query in natural language", "Give me the table of the objects lable, device time and speed for the last 1 hour.")

        translate_button = st.button("Translate to SQL")

        if translate_button:
            sql_query = nl_to_sql(schema_text, nl_query, openrouter_api_key)
            st.markdown("**Translated SQL Query:**")
           # st.code(sql_query, language='sql')

            # Execute the SQL Query
            try:
                df = pd.read_sql(sql_query, conn)
                st.session_state["df"] = df
                st.dataframe(df)
            except Exception as e:
                st.error(f"Query execution error: {e}")

    # Visualization of results
    if "df" in st.session_state:
        df = st.session_state["df"]
        if not df.empty:
            st.subheader("Plot Data")

            x_axis = st.selectbox("Select X-axis", df.columns, key="x_axis")
            y_axis = st.selectbox("Select Y-axis", df.columns, key="y_axis")

            plot_button = st.button("Plot Results")

            if plot_button:
                fig = px.bar(df, x=x_axis, y=y_axis, title="Data Visualization")
                st.plotly_chart(fig)
