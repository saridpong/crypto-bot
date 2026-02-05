"""
Binance DCA Bot - Main Script
==============================
บอท DCA อัตโนมัติ พร้อมระบบป้องกันความเสี่ยง
"""

import ccxt
import time
import csv
import os
from datetime import datetime, timedelta
from config import *

class DCABot:
    def __init__(self):
        print("🤖 เริ่มต้น DCA Bot...")
        
        # เชื่อมต่อ Binance
        self.exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'sandbox': PAPER_TRADING,  # ใช้ testnet ถ้าเป็น paper trading
            'options': {
                'defaultType': 'spot'
            }
        })
        
        if PAPER_TRADING:
            print("📝 โหมด Paper Trading (ไม่ใช้เงินจริง)")
            self.exchange.set_sandbox_mode(True)
        else:
            print("💰 โหมด Live Trading (ใช้เงินจริง!)")
        
        # State
        self.total_invested = 0
        self.total_coins = 0
        self.average_buy_price = 0
        self.last_buy_time = None
        self.last_buy_price = None
        self.trades = []
        
        # โหลดข้อมูลเก่า
        self.load_state()
        
    def load_state(self):
        """โหลดข้อมูลจากไฟล์"""
        state_file = "bot_state.txt"
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    key, value = line.strip().split('=')
                    if key == 'total_invested':
                        self.total_invested = float(value)
                    elif key == 'total_coins':
                        self.total_coins = float(value)
                    elif key == 'average_buy_price':
                        self.average_buy_price = float(value)
                    elif key == 'last_buy_price':
                        self.last_buy_price = float(value) if value != 'None' else None
            print(f"📂 โหลดข้อมูลเก่า: ลงทุนแล้ว ${self.total_invested:.2f}, ถือ {self.total_coins:.8f} coins")
    
    def save_state(self):
        """บันทึกข้อมูล"""
        with open("bot_state.txt", 'w') as f:
            f.write(f"total_invested={self.total_invested}\n")
            f.write(f"total_coins={self.total_coins}\n")
            f.write(f"average_buy_price={self.average_buy_price}\n")
            f.write(f"last_buy_price={self.last_buy_price}\n")
    
    def get_price(self):
        """ดึงราคาปัจจุบัน"""
        ticker = self.exchange.fetch_ticker(SYMBOL)
        return ticker['last']
    
    def get_balance(self):
        """ดึงยอดเงินคงเหลือ"""
        balance = self.exchange.fetch_balance()
        usdt = balance['USDT']['free'] if 'USDT' in balance else 0
        coin = SYMBOL.split('/')[0]
        coin_balance = balance[coin]['free'] if coin in balance else 0
        return usdt, coin_balance
    
    def log_trade(self, action, price, amount, total, reason):
        """บันทึก log การเทรด"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # เขียนลงไฟล์
        file_exists = os.path.exists(LOG_FILE)
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'action', 'price', 'amount', 'total_usdt', 'reason', 'total_invested', 'total_coins', 'avg_price'])
            writer.writerow([timestamp, action, price, amount, total, reason, self.total_invested, self.total_coins, self.average_buy_price])
        
        # แสดงผล
        emoji = "📈" if action == "BUY" else "📉"
        print(f"{emoji} [{timestamp}] {action}: {amount:.8f} @ ${price:.2f} = ${total:.2f} ({reason})")
    
    def buy(self, amount_usdt, reason="DCA"):
        """ซื้อเหรียญ"""
        try:
            price = self.get_price()
            coin_amount = amount_usdt / price
            
            if PAPER_TRADING:
                # Paper trading - จำลองการซื้อ
                print(f"📝 [Paper] ซื้อ {coin_amount:.8f} @ ${price:.2f}")
            else:
                # Live trading
                order = self.exchange.create_market_buy_order(SYMBOL, coin_amount)
                coin_amount = order['filled']
                price = order['average']
            
            # อัพเดท state
            self.total_invested += amount_usdt
            self.total_coins += coin_amount
            self.average_buy_price = self.total_invested / self.total_coins if self.total_coins > 0 else 0
            self.last_buy_time = datetime.now()
            self.last_buy_price = price
            
            self.log_trade("BUY", price, coin_amount, amount_usdt, reason)
            self.save_state()
            
            return True
            
        except Exception as e:
            print(f"❌ ซื้อไม่สำเร็จ: {e}")
            return False
    
    def sell(self, percentage, reason="Take Profit"):
        """ขายเหรียญ"""
        try:
            if self.total_coins <= 0:
                print("⚠️ ไม่มีเหรียญให้ขาย")
                return False
            
            price = self.get_price()
            sell_amount = self.total_coins * (percentage / 100)
            usdt_received = sell_amount * price
            
            if PAPER_TRADING:
                print(f"📝 [Paper] ขาย {sell_amount:.8f} @ ${price:.2f}")
            else:
                order = self.exchange.create_market_sell_order(SYMBOL, sell_amount)
                sell_amount = order['filled']
                usdt_received = order['cost']
            
            # อัพเดท state
            cost_basis = sell_amount * self.average_buy_price
            profit = usdt_received - cost_basis
            
            self.total_coins -= sell_amount
            self.total_invested -= cost_basis
            
            self.log_trade("SELL", price, sell_amount, usdt_received, f"{reason} (P/L: ${profit:.2f})")
            self.save_state()
            
            return True
            
        except Exception as e:
            print(f"❌ ขายไม่สำเร็จ: {e}")
            return False
    
    def check_signals(self):
        """ตรวจสอบสัญญาณซื้อ/ขาย"""
        price = self.get_price()
        now = datetime.now()
        
        print(f"\n💹 ราคาปัจจุบัน: ${price:.2f}")
        print(f"💰 ลงทุนแล้ว: ${self.total_invested:.2f} / ${TOTAL_BUDGET}")
        print(f"🪙 ถือเหรียญ: {self.total_coins:.8f}")
        print(f"📊 ราคาเฉลี่ยที่ซื้อ: ${self.average_buy_price:.2f}")
        
        if self.total_coins > 0:
            current_value = self.total_coins * price
            profit_loss = current_value - self.total_invested
            profit_pct = (profit_loss / self.total_invested * 100) if self.total_invested > 0 else 0
            print(f"💵 มูลค่าปัจจุบัน: ${current_value:.2f} ({profit_pct:+.2f}%)")
        
        # ===== CHECK STOP LOSS =====
        if self.total_coins > 0 and self.average_buy_price > 0:
            loss_pct = ((self.average_buy_price - price) / self.average_buy_price) * 100
            if loss_pct >= STOP_LOSS_PERCENTAGE:
                print(f"🚨 STOP LOSS! ขาดทุน {loss_pct:.2f}%")
                self.sell(100, f"Stop Loss ({loss_pct:.2f}%)")
                return
        
        # ===== CHECK TAKE PROFIT =====
        if self.total_coins > 0 and self.average_buy_price > 0:
            profit_pct = ((price - self.average_buy_price) / self.average_buy_price) * 100
            if profit_pct >= TAKE_PROFIT_PERCENTAGE:
                print(f"🎉 TAKE PROFIT! กำไร {profit_pct:.2f}%")
                self.sell(TAKE_PROFIT_SELL_PERCENTAGE, f"Take Profit ({profit_pct:.2f}%)")
                return
        
        # ===== CHECK BUDGET =====
        if self.total_invested >= TOTAL_BUDGET:
            print("⚠️ ใช้งบหมดแล้ว รอ Take Profit หรือ Stop Loss")
            return
        
        # ===== DCA BUY =====
        should_buy = False
        buy_amount = BUY_AMOUNT
        reason = "DCA"
        
        # เช็คเวลา DCA
        if self.last_buy_time is None:
            should_buy = True
            reason = "First Buy"
        elif (now - self.last_buy_time) >= timedelta(hours=DCA_INTERVAL_HOURS):
            should_buy = True
            reason = "DCA Schedule"
        
        # เช็ค Dip Buy
        if self.last_buy_price and not should_buy:
            dip_pct = ((self.last_buy_price - price) / self.last_buy_price) * 100
            if dip_pct >= DIP_BUY_PERCENTAGE:
                should_buy = True
                buy_amount = BUY_AMOUNT * DIP_BUY_MULTIPLIER
                reason = f"Dip Buy ({dip_pct:.2f}%)"
        
        # ซื้อ
        if should_buy:
            remaining_budget = TOTAL_BUDGET - self.total_invested
            buy_amount = min(buy_amount, remaining_budget)
            
            if buy_amount >= 10:  # Binance minimum
                self.buy(buy_amount, reason)
            else:
                print("⚠️ งบไม่พอสำหรับการซื้อขั้นต่ำ")
        else:
            print("⏳ รอสัญญาณซื้อ...")
    
    def run(self):
        """รันบอทต่อเนื่อง"""
        print("\n" + "="*50)
        print("🚀 DCA Bot เริ่มทำงาน!")
        print(f"📊 เทรดคู่: {SYMBOL}")
        print(f"💵 งบทั้งหมด: ${TOTAL_BUDGET}")
        print(f"⏰ DCA ทุก: {DCA_INTERVAL_HOURS} ชั่วโมง")
        print("="*50)
        
        while True:
            try:
                self.check_signals()
                
                # รอ 5 นาที แล้วเช็คอีกครั้ง
                print(f"\n⏳ เช็คอีกครั้งใน 5 นาที...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("\n👋 หยุดบอท...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)

def main():
    # เช็ค API Key
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ กรุณาใส่ API Key ใน config.py ก่อน!")
        print("📖 วิธีสร้าง: https://www.binance.com/en/my/settings/api-management")
        return
    
    bot = DCABot()
    bot.run()

if __name__ == "__main__":
    main()
