def build_container(name, capacity_ml, material="glass", color="blue", icon="🥤"):
    return {
        "name": name,
        "capacity_ml": capacity_ml,
        "material": material,
        "color": color,
        "icon": icon,
        "usage_count": 0,
        "is_full": True,
    }


def refill_container(container):
    if container is None:
        return
    container["is_full"] = True
    container["usage_count"] = container.get("usage_count", 0) + 1


def empty_container(container):
    if container is None:
        return
    container["is_full"] = False
