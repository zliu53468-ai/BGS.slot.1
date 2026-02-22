from collections import deque

class SlotEngine:
    def __init__(self, window=200):
        self.history = deque(maxlen=window)
        self.spin_count = 0
        self.last_bonus_spin = 0
        self.big_wins = deque(maxlen=100)

    def add_spin(self, bet, win, is_bonus):
        self.spin_count += 1
        self.history.append((bet, win))

        if is_bonus:
            self.last_bonus_spin = self.spin_count

        if bet > 0 and win / bet >= 20:
            self.big_wins.append(1)
        else:
            self.big_wins.append(0)

    def rtp(self, last_n):
        data = list(self.history)[-last_n:]
        total_bet = sum(b for b, _ in data)
        total_win = sum(w for _, w in data)
        if total_bet == 0:
            return 0
        return total_win / total_bet

    def bonus_gap(self):
        return self.spin_count - self.last_bonus_spin

    def big_win_density(self):
        if len(self.big_wins) == 0:
            return 0
        return sum(self.big_wins) / len(self.big_wins)

    def analyze(self):
        rtp30 = self.rtp(30)
        rtp50 = self.rtp(50)
        rtp100 = self.rtp(100)
        gap = self.bonus_gap()
        density = self.big_win_density()

        return {
            "rtp30": round(rtp30, 3),
            "rtp50": round(rtp50, 3),
            "rtp100": round(rtp100, 3),
            "bonus_gap": gap,
            "big_win_density": round(density, 3),
            "total_spins": self.spin_count
        }
