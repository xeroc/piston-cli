import json


class DotDict(dict):

    def __init__(self, keys, values):
        """ This class simplifies the use of "."-separated
            keys when defining a nested dictionary:::

                >>> keys = ['profile.url', 'profile.img']
                >>> values = ["http:", "foobar"]
                >>> print(Profile(keys, values))

                {"profile": {"url": "http:", "img": "foobar"}}

        """
        tree = {}
        for i, item in enumerate(keys):
            t = tree
            parts = item.split('.')
            for j, part in enumerate(parts):
                if j < len(parts) - 1:
                    t = t.setdefault(part, {})
                else:
                    t[part] = values[i]
        self.tree = tree


class Profile(DotDict):
    """ This class is a template to model a user's on-chain
        profile according to

            * https://github.com/adcpm/steemscript
    """

    def __init__(self, *args, **kwargs):
        super(Profile, self).__init__(*args, **kwargs)

    def __str__(self):
        return json.dumps(self.tree)


if __name__ == '__main__':
    keys = ['profile.url', 'profile.img']
    values = ["http:", "foobar"]
    print(Profile(keys, values))
