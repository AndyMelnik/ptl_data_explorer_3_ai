import streamlit as st
import pandas as pd
import pg8000
import plotly.express as px
import openai
import PyPDF2

# Function to read and extract text from PDF schema
def extract_schema(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    schema_text = ""
    for page in reader.pages:
        schema_text += page.extract_text()
    return schema_text

# Function to translate natural language to SQL
def nl_to_sql(schema, nl_query):
    prompt = f"""
    Given the database schema described below, translate the following natural language query into SQL:

    Database Schema:
    {schema}

    Natural Language Query:
    """ + nl_query + """\n
    SQL Query:
    """

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
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
st.title("Enhanced PTL Database Explorer")

with st.sidebar:
    st.header("Database Connection")
    host = st.text_input("Host", value="hostname")
    dbname = st.text_input("Database Name", value="client_XXXXXXX")
    user = st.text_input("Username", value="client_XXXXXXX_user")
    password = st.text_input("Password", type="password")
    port = st.text_input("Port", value="5432")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
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

    if pdf_schema and openai_api_key:
        openai.api_key = openai_api_key
        schema_text = extract_schema(pdf_schema)
        st.subheader("Natural Language Query")
        nl_query = st.text_area("Enter your query in natural language", "Show top 10 objects with the highest revenue.")

        translate_button = st.button("Translate to SQL")

        if translate_button:
            sql_query = nl_to_sql(schema_text, nl_query)
            st.markdown("**Translated SQL Query:**")
            st.code(sql_query, language='sql')

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
