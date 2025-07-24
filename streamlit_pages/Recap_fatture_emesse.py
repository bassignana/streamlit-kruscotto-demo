import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import invoice_xml_processor

def create_monthly_summary():
    """Create monthly summary table like the HTML structure"""
    
    # Sample data - replace with your actual session state data
    sales_monthly = {1: 1250.50, 2: 3400.00, 3: 850.75}  # st.session_state.sales_invoices
    purchase_monthly = {1: 780.00, 2: 1200.50, 3: 450.25}  # st.session_state.purchase_invoices
    
    months = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    
    # Create table data with all three rows in one table
    summary_data = {'': ['Fatture di Vendita', 'Fatture di Acquisto', 'Saldo']}
    saldo_row = []
    
    for i, month in enumerate(months, 1):
        sales = sales_monthly.get(i, 0.0)
        purchase = purchase_monthly.get(i, 0.0)
        balance = sales - purchase
        
        summary_data[month] = [f"{sales:,.2f}", f"{purchase:,.2f}", f"{balance:,.2f}"]
        saldo_row.append(balance)
    
    df = pd.DataFrame(summary_data)
    
    return df, saldo_row

def view_financial_summary():
    """Display financial summary tab"""
    st.subheader("📊 Riepilogo Finanziario")
    
    # Create summary table
    summary_df, saldo_data = create_monthly_summary()
    
    # Display the complete table with saldo included
    st.dataframe(summary_df.set_index(''), use_container_width=True)
    
    # Create chart
    months = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    sales_data = [1250.50, 3400.00, 850.75] + [0] * 9  # Sample data
    purchase_data = [780.00, 1200.50, 450.25] + [0] * 9  # Sample data
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Fatture di Vendita',
        x=months,
        y=sales_data,
        marker_color='rgb(56, 189, 248)',
        opacity=0.85
    ))
    
    fig.add_trace(go.Bar(
        name='Fatture di Acquisto',
        x=months,
        y=purchase_data,
        marker_color='rgb(74, 222, 128)',
        opacity=0.85
    ))
    
    fig.update_layout(
        title='Andamento Mensile',
        xaxis_title='',
        yaxis_title='Euro',
        barmode='group',
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    total_sales = sum(sales_data)
    total_purchases = sum(purchase_data)
    net_balance = total_sales - total_purchases
    
    with col1:
        st.metric("Totale Vendite", f"€ {total_sales:,.2f}")
    with col2:
        st.metric("Totale Acquisti", f"€ {total_purchases:,.2f}")
    with col3:
        st.metric("Saldo Netto", f"€ {net_balance:,.2f}")

# Main App
def main():
    st.session_state

    st.set_page_config(page_title="Sistema Gestione Fatture", page_icon="📄", layout="wide")
                
    invoice_xml_processor.invoice_xml_processor_page()
    
    view_financial_summary()

if __name__ == "__main__":
    main()