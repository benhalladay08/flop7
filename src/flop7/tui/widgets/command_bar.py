import urwid


class CommandBar(urwid.WidgetWrap):
	"""Minimal command input widget used in the footer."""

	def __init__(self, prompt: str = "> ") -> None:
		self.edit = urwid.Edit(caption=prompt)
		self._container = urwid.AttrMap(self.edit, "command")
		super().__init__(self._container)

	def get_text(self) -> str:
		return self.edit.edit_text

	def clear(self) -> None:
		self.edit.edit_text = ""


