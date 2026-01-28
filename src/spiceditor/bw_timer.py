import platform
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont


class CountdownTimer(QWidget):
    def __init__(self, hours=0, minutes=0, seconds=0, auto_start=False, show_buttons=True):
        super().__init__()

        # Store initial time
        self.initial_hours = hours
        self.initial_minutes = minutes
        self.initial_seconds = seconds
        self.auto_start = auto_start
        self.show_buttons = show_buttons

        # Calculate total seconds
        self.total_seconds = hours * 3600 + minutes * 60 + seconds
        self.remaining_seconds = self.total_seconds

        # Timer running state
        self.is_running = False
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Main layout
        layout = QVBoxLayout()

        # Time display label
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFont(QFont('Arial', 48, QFont.Bold))
        layout.addWidget(self.time_label)

        # Buttons layout
        button_layout = QHBoxLayout()

        # Start/Pause button
        self.start_pause_btn = QPushButton('Start')
        self.start_pause_btn.clicked.connect(self.toggle_timer)
        button_layout.addWidget(self.start_pause_btn)

        # Reset button
        self.reset_btn = QPushButton('Reset')
        self.reset_btn.clicked.connect(self.reset_timer)
        button_layout.addWidget(self.reset_btn)

        if self.show_buttons:
            layout.addLayout(button_layout)

        self.setLayout(layout)

        # QTimer for countdown
        self.timer = QTimer()
        self.timer.timeout.connect(self.countdown)

        if self.auto_start:
            self.toggle_timer()

        self.update_display()

    def update_display(self):
        """Update the time display label"""
        hours = self.remaining_seconds // 3600
        minutes = (self.remaining_seconds % 3600) // 60
        seconds = self.remaining_seconds % 60

        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.time_label.setText(time_str)

        # Change color when time is running out
        if 10 >= self.remaining_seconds > 0:
            self.time_label.setStyleSheet("color: orange;")
        elif self.remaining_seconds == 0:
            self.time_label.setStyleSheet("color: red;")
        else:
            self.time_label.setStyleSheet("color: black;")

    def countdown(self):
        """Decrease time by 1 second"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_display()
        else:
            self.timer.stop()
            self.is_running = False
            self.start_pause_btn.setText('Start')
            print("Timer finished!")
            try:
                self.play_alarm_sound()
            except:
                pass

    def toggle_timer(self):
        """Start or pause the timer"""
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.start_pause_btn.setText('Resume')
        else:
            if self.remaining_seconds > 0:
                self.timer.start(1000)  # Update every 1000ms (1 second)
                self.is_running = True
                self.start_pause_btn.setText('Pause')

    def reset_timer(self):
        """Reset timer to initial value"""
        self.timer.stop()
        self.is_running = False
        self.remaining_seconds = self.total_seconds
        self.start_pause_btn.setText('Start')
        self.update_display()

    def play_alarm_sound(self):
        """Play a sound when timer finishes"""
        try:
            system = platform.system()

            if system == "Windows":
                # Windows: use winsound
                import winsound
                # Play beep 3 times
                for i in range(3):
                    QTimer.singleShot(i * 600, lambda: winsound.Beep(1000, 400))
            else:
                # Fallback: just print bell character (works on most terminals)
                for _ in range(3):
                    print('\a')  # ASCII bell character
        except Exception as e:
            # Fallback: just print bell character (works on most terminals)
            print(f"Sound method failed: {e}")
            for _ in range(3):
                print('\a')  # ASCII bell character


# Example usage
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create a timer widget with 0 hours, 5 minutes, 30 seconds
    timer_widget = CountdownTimer(hours=0, minutes=0, seconds=3, auto_start=True, show_buttons=False)
    timer_widget.setWindowTitle('Countdown Timer')
    timer_widget.resize(400, 200)
    timer_widget.show()

    sys.exit(app.exec_())
