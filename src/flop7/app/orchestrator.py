from flop7.tui.app import TUIApp

class App:
    def __init__(self):
        self.tui = TUIApp(self.handle_user_command)

    def run(self):
        self.tui.run()

    def handle_user_command(self, command: str):
        ...