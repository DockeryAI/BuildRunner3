extends Node

enum Severity { TRACE, DEBUG, INFO, WARN, ERROR }

const MAX_ENTRIES := 500
const BRLOGGER_LOG_PATH := "user://logs/brlogger.log"
const EVENTBUS_LOG_PATH := "user://logs/eventbus.log"
const ENGINE_LOG_PATH := "user://logs/engine.log"

var _entries: Array[Dictionary] = []
var _sinks: Dictionary = {}
var _engine_timer: Timer


func _ready() -> void:
	_ensure_logs_dir()
	_open_sink("brlogger", BRLOGGER_LOG_PATH)
	_open_sink("eventbus", EVENTBUS_LOG_PATH)
	_open_sink("engine", ENGINE_LOG_PATH)
	_engine_timer = Timer.new()
	_engine_timer.wait_time = 1.0
	_engine_timer.autostart = true
	_engine_timer.one_shot = false
	_engine_timer.timeout.connect(_sample_engine_metrics)
	add_child(_engine_timer)
	info("system", "BRLogger initialized")


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		flush_all()


func trace(channel: String, msg: String, data: Variant = null) -> void:
	_log(Severity.TRACE, channel, msg, data, "brlogger")


func debug(channel: String, msg: String, data: Variant = null) -> void:
	_log(Severity.DEBUG, channel, msg, data, "brlogger")


func info(channel: String, msg: String, data: Variant = null) -> void:
	_log(Severity.INFO, channel, msg, data, "brlogger")


func warn(channel: String, msg: String, data: Variant = null) -> void:
	_log(Severity.WARN, channel, msg, data, "brlogger")


func error(channel: String, msg: String, data: Variant = null) -> void:
	_log(Severity.ERROR, channel, msg, data, "brlogger")


func event(name: String, data: Variant = null) -> void:
	_log(Severity.INFO, "eventbus", name, data, "eventbus")


func flush_all() -> void:
	for sink in _sinks.values():
		if sink is FileAccess:
			sink.flush()
			sink.close()
	_sinks.clear()


func get_entries() -> Array[Dictionary]:
	return _entries.duplicate(true)


func _log(severity: Severity, channel: String, msg: String, data: Variant, sink_name: String) -> void:
	var entry := {
		"ts": Time.get_datetime_string_from_system(),
		"severity": _severity_name(severity),
		"channel": channel,
		"msg": msg,
		"data": data,
	}
	_entries.append(entry)
	if _entries.size() > MAX_ENTRIES:
		_entries.pop_front()
	_write_sink_line(sink_name, _format_entry(entry))


func _sample_engine_metrics() -> void:
	var payload := {
		"fps": Performance.get_monitor(Performance.TIME_FPS),
		"memory_static": Performance.get_monitor(Performance.MEMORY_STATIC),
		"memory_peak": Performance.get_monitor(Performance.MEMORY_STATIC_MAX),
	}
	_log(Severity.DEBUG, "engine", "runtime sample", payload, "engine")


func _severity_name(severity: Severity) -> String:
	match severity:
		Severity.TRACE:
			return "TRACE"
		Severity.DEBUG:
			return "DEBUG"
		Severity.INFO:
			return "INFO"
		Severity.WARN:
			return "WARN"
		Severity.ERROR:
			return "ERROR"
	return "INFO"


func _format_entry(entry: Dictionary) -> String:
	var data_text := "null"
	if entry["data"] != null:
		data_text = JSON.stringify(entry["data"])
	return "%s [%s] (%s) %s | data=%s" % [
		entry["ts"],
		entry["severity"],
		entry["channel"],
		entry["msg"],
		data_text,
	]


func _ensure_logs_dir() -> void:
	DirAccess.make_dir_recursive_absolute("user://logs")


func _open_sink(name: String, path: String) -> void:
	var file := FileAccess.open(path, FileAccess.READ_WRITE)
	if file == null:
		file = FileAccess.open(path, FileAccess.WRITE_READ)
	if file == null:
		push_warning("BRLogger could not open sink at %s" % path)
		return
	file.seek_end()
	_sinks[name] = file


func _write_sink_line(name: String, line: String) -> void:
	var sink = _sinks.get(name)
	if sink == null:
		return
	sink.store_line(line)
	sink.flush()
