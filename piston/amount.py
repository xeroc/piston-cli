class Amount(object):
    def __init__(self, amountString):
        self.amount, self.asset = amountString.split(" ")
        self.amount = float(self.amount)

    def __str__(self):
        if self.asset == "SBD":
            prec = 3
        elif self.asset == "STEEM":
            prec = 3
        elif self.asset == "VESTS":
            prec = 6
        else:
            prec = 6
        return "{:.{prec}f} {}".format(self.amount, self.asset, prec=prec)
