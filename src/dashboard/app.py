import sys
import can
from PySide6.QtCore import Qt, QSettings, QPoint, QSize
from PySide6.QtGui import QCloseEvent, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
)

from motor import CyberGearMotor

from dashboard.parameters_table import MotorParametersWidget
from dashboard.controller.controller_dock import MotorControllerDockWidget
from dashboard.motor_state import MotorStateWidget
from dashboard.watcher import MotorWatcher

CAN_BITRATE = 1000000


class AppWindow(QMainWindow):
    bus: can.Bus
    motor: CyberGearMotor
    watcher: MotorWatcher
    settings: QSettings

    def __init__(
        self, channel: str, interface: str, motor_id: int, verbose: bool = False
    ):
        super().__init__()
        self.settings = QSettings("jgillick", "PyCyberGearDashboard")

        # Connect to motor
        self.connect(channel, interface, motor_id, verbose)

        # UI
        self.restore_window_pos()
        self.setWindowTitle("CyberGear Dashboard")
        self.build_layout()
        self.build_menubar()

    def build_layout(self):
        """Construct the layout"""
        layout = QVBoxLayout()

        self.state_dock = MotorStateWidget(self.motor, self)
        self.parameter_dock = MotorParametersWidget(self.motor, self)
        self.controller_dock = MotorControllerDockWidget(self.motor, self)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.state_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.parameter_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.controller_dock)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def build_menubar(self):
        """Setup the app menubar"""
        view_motor_state = QAction("Motor state", self)
        view_motor_state.setCheckable(True)

        view_parameters = QAction("Parameters", self)
        view_parameters.setCheckable(True)

        view_control = QAction("Control", self)
        view_control.setCheckable(True)

        menu = self.menuBar()

        view_menu = menu.addMenu("&View")
        view_menu.addAction(view_motor_state)
        view_menu.addAction(view_parameters)
        view_menu.addAction(view_control)

        # Connect menus to dock widgets
        view_motor_state.toggled.connect(self.state_dock.setVisible)
        self.state_dock.visibilityChanged.connect(view_motor_state.setChecked)

        self.parameter_dock.visibilityChanged.connect(view_parameters.setChecked)
        view_parameters.toggled.connect(self.parameter_dock.setVisible)

        view_control.toggled.connect(self.controller_dock.setVisible)
        self.controller_dock.visibilityChanged.connect(view_control.setChecked)

    def connect(
        self, channel: str, interface: str, motor_id: int, verbose: bool
    ) -> bool:
        """Connect to the CAN bus and the motor controller"""
        try:
            self.bus = can.interface.Bus(
                interface=interface,
                channel=channel,
                bitrate=CAN_BITRATE,
            )
            print("Connected!")

            # Create the motor controller
            self.motor = CyberGearMotor(motor_id, bus=self.bus, verbose=verbose)
            self.motor.enable()
            self.motor.stop()

            # Regularly poll the motor for updates
            self.watcher = MotorWatcher(self.motor)
            self.watcher.start()
        except Exception as e:
            alert = QMessageBox()
            alert.setText(f"Could not connect to the motor\n{e}")
            alert.exec()
            self.close()
        return True

    def save_window_pos(self):
        """Save the window position and size to settings"""
        self.settings.setValue("win.pos", self.pos())
        self.settings.setValue("win.size", self.size())

    def restore_window_pos(self):
        """Restore the window size and position from last session"""
        pos = self.settings.value("win.pos", defaultValue=QPoint(50, 50))
        size = self.settings.value("win.size", defaultValue=QSize(900, 600))
        self.move(pos)
        self.resize(size)

    def closeEvent(self, event: QCloseEvent):
        """Cleanup before we exit"""

        if self.motor:
            self.motor.stop()
            self.motor.disconnect()
        if self.bus:
            # Only save window position if we had connected to the bus
            self.save_window_pos()

            #  Close the bus
            self.bus.shutdown()
        event.accept()


def openDashboard(channel: str, interface: str, motor_id: int, verbose: bool = False):
    app = QApplication(sys.argv)
    window = AppWindow(channel, interface, motor_id, verbose)
    window.show()
    app.exec()
