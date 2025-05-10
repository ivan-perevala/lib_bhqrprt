# Python Logging and Blender Integration Package

This Python package is designed to streamline the process of logging for both Python applications and Blender extension development. It provides advanced logging features such as automatic log file management, colored console outputs, and a specialized API for seamless integration with Blender's operator execution processes. Whether you're developing for Blender or a general Python project, this package ensures an efficient, structured, and easy-to-read logging experience.

![Report and Log](./docs/_static/images/report_and_log.jpg)

## Core Features:

1. **Simultaneous Console and File Logging:**
   The package offers the ability to log messages both to the console and to log files simultaneously. Console logs are color-coded based on severity level for quick readability, while detailed logs are saved in a structured format in log files.

   - **Colored Console Output:**
     Logs are color-coded by severity (e.g., INFO, WARNING, ERROR), making it easy for developers to distinguish between different log levels at a glance. This improves the debugging process by providing visual clarity.
   
   - **Log Level Customization:**
     The package allows developers to control what log level is displayed in the console while all levels are stored in the log files. This way, you can focus on specific messages in real-time while still capturing a full log history for future reference.

2. **Log File Rotation and Cleanup:**
   The package automates the cleanup of old log files, ensuring that your log directory remains manageable over time.

   - **Automatic Log Deletion:**
     When a new log file is created, older logs are automatically deleted based on a user-defined retention policy. You can configure how many logs to keep, preventing your log directory from becoming overcrowded and saving disk space.

   Example:
   ```python
   import bhqrprt
   logs_directory = os.path.join(os.path.dirname(__file__), "logs")
   bhqrprt.purge_old_logs(directory=logs_directory, max_num_logs=30)
   bhqrprt.setup_logger(directory=logs_directory)
   log = logging.getLogger(name=__name__)
   ```

   In this example, old logs are purged automatically, keeping only the most recent 30 log files.

3. **Blender Addon Integration:**
   The package provides a specialized API designed for developers creating Blender addons. This API helps you track operator execution, log settings, and report messages both to the UI and to the log files simultaneously.

   - **Operator Execution Logs:**
     Track the start and end times of Blender operator executions and automatically log these events. This is particularly useful when performance tracking is important or when you need a clear audit trail for Blender's operations.

   - **Logging Settings and Scene Properties:**
     The package allows developers to log Blender settings and scene properties easily. This is valuable when debugging or sharing the current state of the Blender environment.

     Example:
     ```python
     log.debug("Loaded with settings:")
     log.debug("Preferences:")
     bhqrprt.log_settings(log, item=addon_pref)
     
     log.debug("Scene:")
     scene: Scene = context.scene
     scene_props: SceneProps = scene.cpp
     bhqrprt.log_settings(log, item=scene_props)
     ```

     In this example, both the extension's preferences and scene properties are logged, providing insights into the current Blender configuration.

   - **Unified Logging and Reporting:**
     Blender operators often provide feedback to the user through `self.report`. With this package, you can log these messages to the log files while still reporting them in the UI, ensuring both user-facing and internal logs are captured.

     Example:
     ```python
     bhqrprt.report_and_log(
         log,
         self,
         level=logging.WARNING,
         message="Active UV map is missing, continue with limited capabilities",
         msgctxt=msgctxt,
     )
     ```

     Here, a message is both reported in Blender's UI and logged, providing a clear trace of what the user saw and what was logged internally.


## License

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue)](https://www.gnu.org/licenses/gpl-3.0)

Copyright © 2022 Ivan Perevala (ivpe).

See [./LICENSE](./LICENSE) file for license.
