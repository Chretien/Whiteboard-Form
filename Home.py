import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import numpy as np
import yaml
from yaml.loader import SafeLoader
from parameters import *
import pymongo
import plotly.express as px

@st.cache_resource
def init_connection():
    return pymongo.MongoClient(f"mongodb+srv://{st.secrets['mongo'].username}:{st.secrets['mongo'].password}@{st.secrets['mongo'].cluster_name}.oanmrag.mongodb.net/?retryWrites=true&w=majority")

area_manager_view = ['Vicente','Lorenzo','Luis','Harry','Carlos']
admin_view = ['Mike','Kyle','Chretien','Trek','Louie']

client = init_connection()

db = client['test']
collection = db['test']

def clean_df_mongo(x):
    df = x.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.iloc[:,1:]
    df = df.drop_duplicates()
    return df

@st.cache_data
def read_wipClone():
    df = pd.read_csv(wipCloneUrl)
    return df
builderCommunity = read_wipClone()

with open('authentication/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

def input_table_creator(key:str):
    df = pd.DataFrame(columns=['Foreman','Builder','Community','Lot','Task Type','Amount'], index=range(5))
    df['Foreman'] = df['Foreman'].astype(pd.CategoricalDtype(foremen))
    df['Builder'] = df['Builder'].astype(pd.CategoricalDtype(np.unique(builderCommunity['Builder'])))
    df['Community'] = df['Community'].astype(pd.CategoricalDtype(np.unique(builderCommunity['Community'])))
    df['Task Type'] = df['Task Type'].astype(pd.CategoricalDtype(task_type))
    df['Amount'] = df['Amount'].astype('float')
    df['Lot'] = df['Lot'].astype('float')
    table_create = st.data_editor(df, use_container_width=True, hide_index=True, key=key, num_rows='dynamic')
    return table_create


name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    username = st.session_state['name']
    authenticator.logout('Logout','sidebar')
    if username in area_manager_view:
        with st.container():
            st.header(f'Welcome {name}')
            
            foremen = AreaManagerForeman[username]

                
            # MAIN APP     
        with st.container():
            report_date = st.date_input('Please Choose a Date','today', format='MM/DD/YYYY')
            input_dataframe = input_table_creator('main_table')
            submit_jobs_to_db = st.button('Submit Jobs')
            
            if submit_jobs_to_db:
                input_dataframe = input_dataframe.dropna(how='all', axis=0)
                input_dataframe['Date'] = report_date.strftime('%m-%d-%Y')
                input_dataframe['Area Manager'] = username
                
                write_table_out = input_dataframe.copy()
                st.table(write_table_out)
                
                try:
                    collection.insert_many(write_table_out.to_dict('records'))
                    st.success('Your jobs have been successfully submitted!')
                    st.session_state['main_table'].clear()
                
                except:
                    st.warning('Please make sure there is data to submit.')
            
            with st.container():
                filter_date = st.date_input('What date would you like to see?',format='MM/DD/YYYY')
                return_df = pd.DataFrame(list(collection.find({"Area Manager":name})))
                return_df['Date'] = pd.to_datetime(return_df['Date'])
                return_df = return_df.query("`Date` == @filter_date")
                total_return_sum = return_df['Amount'].sum()
                
                st.metric(f'Total Sales for {filter_date.strftime("%B %d, %Y")}',"{:,.2f}".format(total_return_sum))
                st.dataframe(return_df.iloc[:,1:], hide_index=True)

    elif username in admin_view:
        today = pd.Timestamp.today().strftime('%B %d, %Y')
        this_month = pd.Timestamp.today().strftime('%B')
        this_month_int = pd.Timestamp.today().month
        with st.sidebar:
            st.write(f"Today is {today}")
            pick_date = st.date_input('View stats for date','today',format="MM/DD/YYYY")
        st.header(f'Admin Panel - {username}', divider='green')
        df_full = pd.DataFrame(list(collection.find()))
        df_full = df_full.pipe(clean_df_mongo)
        
        
        # VIEWS
        area_manager_grouping = df_full.groupby(['Area Manager','Builder'])['Amount'].sum()
        area_manager_grouping_date = df_full.set_index('Date').groupby('Area Manager').resample('d')['Amount'].sum().reset_index()
        total_for_current_month_all = df_full.query("`Date`.dt.month == @this_month_int")['Amount'].sum()
        total_for_current_pick_date = df_full.query("`Date` == @pick_date")['Amount'].sum()
        
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                st.metric(f"Total for {this_month}", "${:,.2f}".format(total_for_current_month_all))
            with col2:
                st.metric(f"Total for {pick_date.strftime('%m/%d/%Y')}", "${:,.2f}".format(total_for_current_pick_date))
                
            st.plotly_chart(px.bar(area_manager_grouping_date, x='Date',y='Amount', color='Area Manager'))
            st.divider()


elif authentication_status is False:
    st.error('Username/Password is incorrect')
    
