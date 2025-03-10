# This is used solely for the setup command
# stores current view information for utilisation
# of a view state variable without unintended
# cross-server data manipulation and consequences


class ViewStateManager(dict):
    def __getitem__(self, key):
        return super().__getitem__(key)

    def __setitem__(self, key, value) -> None:
        return super().__setitem__(key, value)
