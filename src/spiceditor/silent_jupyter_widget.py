from qtconsole.rich_jupyter_widget import RichJupyterWidget


class SilentRichJupyterWidget(RichJupyterWidget):
    def __init__(self):
        # self.custom_control = OverriddenBehaviorTextEdit
        super().__init__()
        self.keys = []
        self.run = None
        self.echo = True
        self._control.installEventFilter(self)

    def _append_custom(self, insert, input, before_prompt=False, *args, **kwargs):
        return super()._append_custom(insert, input, before_prompt=before_prompt, *args, **kwargs)

    def _append_plain_text(self, text, before_prompt=False):
        super()._append_plain_text(text, before_prompt=before_prompt)

    def set_echo(self, value):
        self.echo = value

    def _set_input_buffer(self, string):
        if self.echo:
            super()._set_input_buffer(string)
        else:
            self._control.clear()

    def _get_input_buffer(self, force=False):
        return super()._get_input_buffer(force)

    input_buffer = property(_get_input_buffer, _set_input_buffer)

    def set_key_override(self, keys):
        self.keys = keys

    def _handle_error(self, msg):
        content = msg.get("content", {})
        if content.get("ename") == "KeyboardInterrupt":
            return  # no mostrar nada
        super()._handle_error(msg)

    def eventFilter(self, watched, event):
        if watched == self._control:
            if event.type() == 6:
                for key, modifier, action, new_event in self.keys:
                    if event.key() == key and event.modifiers() == modifier:
                        if action == "run":
                            new_event()
                        elif action == "disable":
                            pass
                        elif action == "replace":
                            super().eventFilter(watched, new_event)
                            # QApplication.postEvent(watched, new_event)
                        return True  # block jupyter from seeing it
        return super().eventFilter(watched, event)
