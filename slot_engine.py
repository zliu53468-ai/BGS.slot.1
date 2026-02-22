from collections import deque
import numpy as np

class SlotEngine:
    def __init__(self, window=200):
        self.history = deque(maxlen=window)
        self.spin_count = 0
        self.last_bonus_spin = 0
        self.last_bet = 10
        self.big_wins = deque(maxlen=100)

    def add_spin(self, bet, win, is_bonus):
        self.spin_count += 1
        self.history.append((bet, win))
        self.last_bet = bet

        if is_bonus:
            self.last_bonus_spin = self.spin_count

        if bet > 0 and win / bet >= 20:
            self.big_wins.append(1)
        else:
            self.big_wins.append(0)

    # ===== 基礎RTP =====
    def rtp(self, n):
        data = list(self.history)[-n:]
        total_bet = sum(b for b, _ in data)
        total_win = sum(w for _, w in data)
        if total_bet == 0:
            return 0
        return total_win / total_bet

    # ===== EMA 平滑 =====
    def ema_rtp(self, alpha=0.2):
        rtp_values = []
        for bet, win in self.history:
            if bet > 0:
                rtp_values.append(win / bet)
        if not rtp_values:
            return 0

        ema = rtp_values[0]
        for val in rtp_values[1:]:
            ema = alpha * val + (1 - alpha) * ema
        return ema

    # ===== 加權RTP模型 =====
    def weighted_rtp(self):
        rtp10 = self.rtp(10)
        rtp30 = self.rtp(30)
        rtp50 = self.rtp(50)

        return (
            rtp10 * 0.5 +
            rtp30 * 0.3 +
            rtp50 * 0.2
        )

    def volatility(self):
        returns = []
        for bet, win in list(self.history)[-50:]:
            if bet > 0:
                returns.append(win / bet)
        if len(returns) < 2:
            return 0
        return np.std(returns)

    def bonus_gap(self):
        return self.spin_count - self.last_bonus_spin

    # ===== 策略判斷 =====
    def next_action(self, rtp_score, vol, gap):
        base = self.last_bet

        # 高波動 → 保守
        if vol > 3:
            return base * 0.7, 20, "高波動保守"

        # 熱機
        if rtp_score > 1.15:
            return base * 1.5, 40, "熱機放大"

        # 冷機
        if rtp_score < 0.75:
            return base * 0.5, 20, "冷機觀察"

        # 正常
        return base, 30, "穩定區"

    def analyze(self):
        rtp_score = self.weighted_rtp()
        ema = self.ema_rtp()
        vol = self.volatility()
        gap = self.bonus_gap()

        next_bet, spins, mode = self.next_action(rtp_score, vol, gap)

        return {
            "total_spins": self.spin_count,
            "rtp_score": round(rtp_score, 3),
            "ema_rtp": round(ema, 3),
            "volatility": round(vol, 3),
            "bonus_gap": gap,
            "next_bet": round(next_bet, 2),
            "next_spins": spins,
            "mode": mode
        }
