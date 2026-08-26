from core.system.metrics_collector import MetricsCollector

def test_metrics_collector_system_metrics_keys():
    collector = MetricsCollector()
    metrics = collector.get_system_metrics()

    expected_keys = {
        "os", "sys_cpu_usage", "sys_cpu_free", "sys_ram_free",
        "sys_disk_free", "swap", "host_uptime_sec", "net"
    }
    assert expected_keys.issubset(metrics.keys())
    assert isinstance(metrics["sys_cpu_usage"], (int, float))
    assert isinstance(metrics["sys_ram_free"], (int, float))
    assert isinstance(metrics["sys_disk_free"], (int, float))
    assert metrics["sys_disk_free"] > 0
    assert metrics["host_uptime_sec"] > 0

def test_metrics_collector_network_speed_calculation():
    collector = MetricsCollector()
    down, up, net_str = collector.calculate_network_speed()
    assert isinstance(down, (int, float))
    assert isinstance(up, (int, float))
    assert isinstance(net_str, str)
    assert len(net_str) > 0

def test_metrics_collector_format_speed():
    collector = MetricsCollector()
    assert "KB/s" in collector.format_speed(500 * 1024)
    assert "MB/s" in collector.format_speed(50 * 1024 * 1024)
    assert "GB/s" in collector.format_speed(2 * 1024 * 1024 * 1024)
