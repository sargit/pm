import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import Dict, List, Tuple
import math

@dataclass
class MarketState:
    bets_history: List[Dict] = None
    current_yes: float = 500.0
    current_no: float = 500.0
    user_yes_bets: float = 0.0  # Сумма денег, поставленных на YES
    user_no_bets: float = 0.0   # Сумма денег, поставленных на NO
    user_yes_profits: float = 0.0  # Обещанная прибыль по YES
    user_no_profits: float = 0.0   # Обещанная прибыль по NO
    bet_amount: float = 10.0
    
    def __post_init__(self):
        self.bets_history = self.bets_history or []
def dynamic_k(initial_yes, initial_no):
    """
    Функция для расчета коэффициента k, который растет по мере увеличения общего пула ликвидности.
    """
    total_liquidity = initial_yes + initial_no
    return 0.05 + 0.05 * math.log10(total_liquidity)  # k увеличивается с ростом ликвидности

def calculate_market_metrics(initial_yes: float, initial_no: float, 
                           bet_amount: float, bet_position: str = "YES") -> Dict:
    new_yes = initial_yes + bet_amount if bet_position == "YES" else initial_yes
    new_no = initial_no + bet_amount if bet_position == "NO" else initial_no
    
    if bet_position == "YES":
        # win_percentage = min(0.9, 0.2 + 0.1 * math.log(1 + bet_amount/initial_no))
        win_percentage = min(
            0.9, 
            0.2 + 0.1 * math.log(1 + bet_amount / math.sqrt(initial_yes * initial_no))
            
        )
        max_possible_win = initial_no * win_percentage
        calculated_win = bet_amount * (initial_no / initial_yes)
        potential_win = float(f"{min(calculated_win, max_possible_win):.2f}")
        available_liquidity = initial_no - potential_win
    else:
        # win_percentage = min(0.9, 0.2 + 0.1 * math.log(1 + bet_amount/initial_yes))
        win_percentage = min(
            0.9, 
            0.2 + 0.1 * math.log(1 + bet_amount / math.sqrt(initial_yes * initial_no))
        )
        max_possible_win = initial_yes * win_percentage
        calculated_win = bet_amount * (initial_yes / initial_no)
        potential_win = float(f"{min(calculated_win, max_possible_win):.2f}")
        available_liquidity = initial_yes - potential_win
    
    return {
        "new_pool": new_yes if bet_position == "YES" else new_no,
        "potential_win": potential_win,
        "new_yes_price": new_yes / (new_yes + new_no),
        "new_no_price": new_no / (new_yes + new_no),
        "available_liquidity": available_liquidity
    }

def show_market_interface():
    st.title("Калькулятор рынка")
    
    # Инициализация состояния
    if 'market_state' not in st.session_state:
        st.session_state.market_state = MarketState()
    
    display_market_status()
    handle_betting()
    
    if st.session_state.market_state.bets_history:
        show_history()
        # Показываем кнопку сброса только если есть история ставок
        if st.button("Сбросить"):
            st.session_state.market_state = MarketState()
            st.rerun()

def display_market_status():
    col1, col2 = st.columns(2)
    
    # YES колонка
    with col1:
        st.write("YES")
        st.metric("Ликвидность", f"${st.session_state.market_state.current_yes:,.2f}")
        st.metric("Сумма ставок", f"${st.session_state.market_state.user_yes_bets:,.2f}")
        st.metric("Объязательства", f"${st.session_state.market_state.user_yes_profits:,.2f}")
    
    # NO колонка
    with col2:
        st.write("NO")
        st.metric("Ликвидность", f"${st.session_state.market_state.current_no:,.2f}")
        st.metric("Сумма ставок", f"${st.session_state.market_state.user_no_bets:,.2f}")
        st.metric("Объязательства", f"${st.session_state.market_state.user_no_profits:,.2f}")

def handle_betting():
    bet_amount = st.number_input("Ставка", value=10, min_value=1, step=1)
    st.session_state.market_state.bet_amount = bet_amount
    
    col1, col2 = st.columns(2)
    
    for position, col in zip(["YES", "NO"], [col1, col2]):
        metrics = calculate_market_metrics(
            st.session_state.market_state.current_yes,
            st.session_state.market_state.current_no,
            bet_amount,
            position
        )
        
        if metrics['available_liquidity'] >= 0:
            with col:
                # Показываем полную сумму выигрыша (ставка + потенциальный выигрыш)
                total_win = bet_amount + metrics['potential_win']
                if st.button(f"Buy {position} to win ${total_win:,.2f}"):
                    process_bet(position, bet_amount, metrics)
                    st.rerun()

def process_bet(position: str, amount: float, metrics: Dict):
    if position == "YES":
        # Добавляем ставку в пул YES
        st.session_state.market_state.current_yes += amount
        # Уменьшаем пул NO на размер потенциального выигрыша
        st.session_state.market_state.current_no -= metrics['potential_win']
        # Записываем сумму ставки
        st.session_state.market_state.user_yes_bets += amount
        # Записываем обязательства (потенциальный выигрыш)
        st.session_state.market_state.user_yes_profits += metrics['potential_win']
    else:
        # Добавляем ставку в пул NO
        st.session_state.market_state.current_no += amount
        # Уменьшаем пул YES на размер потенциального выигрыша
        st.session_state.market_state.current_yes -= metrics['potential_win']
        # Записываем сумму ставки
        st.session_state.market_state.user_no_bets += amount
        # Записываем обязательства (потенциальный выигрыш)
        st.session_state.market_state.user_no_profits += metrics['potential_win']
    
    st.session_state.market_state.bets_history.append({
        'position': position,
        'amount': amount,
        'yes_price': metrics['new_yes_price'],
        'no_price': metrics['new_no_price'],
        'potential_win': metrics['potential_win']
    })

def show_history():
    df = pd.DataFrame(st.session_state.market_state.bets_history)
    st.dataframe(df)
    
    fig = go.Figure()
    for price_type, title in [('yes_price', 'YES'), ('no_price', 'NO')]:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[price_type],
            name=title, mode='lines+markers'
        ))
    
    fig.update_layout(
        title='История цен',
        xaxis_title='Ставка',
        yaxis_title='Цена ($)'
    )
    st.plotly_chart(fig)

if __name__ == "__main__":
    show_market_interface()
