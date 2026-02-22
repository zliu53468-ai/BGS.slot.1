from collections import deque
import numpy as np

class SlotEngine:
    def __init__(self, bankroll):
        self.bankroll = bankroll
        self.balance = bankroll
        self.history = deque(maxlen=200)
        self.spin_count = 0
        self.last_bet = 0

        self.max_bet_ratio = 0.03
        self.risk_ratio = 0.02

        # ===== 新增探測期 =====
        self.probe_spins = 20   # 前20轉為探測期
        self.probe_ratio = 0.01 # 探測期固定1%

    def add_spin(self, bet, win):
        self.spin_count += 1
        self.last_bet = bet
        self.balance = self.balance - bet + win
        self.history.append((bet, win))

    def rtp(self, n):
        data = list(self.history)[-n:]
        total_bet = sum(b for b, _ in data)
        total_win = sum(w for _, w in data)
        return total_win / total_bet if total_bet > 0 else 0

    def weighted_rtp(self):
        return (
            self.rtp(10) * 0.5 +
            self.rtp(30) * 0.3 +
            self.rtp(50) * 0.2
        )

    def risk_control_bet(self, raw_bet):
        max_allowed = self.bankroll * self.max_bet_ratio
        balance_limit = self.balance * 0.05
        return min(raw_bet, max_allowed, balance_limit)

    def next_action(self):

        # ===== 探測期 =====
        if self.spin_count < self.probe_spins:
            bet = self.bankroll * self.probe_ratio
            return round(bet, 2), self.probe_spins - self.spin_count, "探測期（固定1%）"

        rtp_score = self.weighted_rtp()
        base_bet = self.bankroll * self.risk_ratio

        # ===== 加入平滑機制避免剛回補就暴力加碼 =====
        if rtp_score > 1.2:
            base_bet *= 1.2
            mode = "溫和放大"
            spins = 30
        elif rtp_score < 0.7:
            base_bet *= 0.8
            mode = "保守模式"
            spins = 20
        else:
            mode = "穩定區"
            spins = 25

        final_bet = self.risk_control_bet(base_bet)

        return round(final_bet, 2), spins, mode

    def analyze(self):

        rtp_score = round(self.weighted_rtp(), 3)
        next_bet, spins, mode = self.next_action()

        stop = ""
        if self.balance <= self.bankroll * 0.5:
            stop = "⚠ 已達50%止損"
        elif self.balance >= self.bankroll * 1.5:
            stop = "🎉 已達50%止盈"

        return {
            "total_spins": self.spin_count,
            "balance": round(self.balance, 2),
            "rtp": rtp_score,
            "next_bet": next_bet,
            "next_spins": spins,
            "mode": mode,
            "stop": stop
        }
