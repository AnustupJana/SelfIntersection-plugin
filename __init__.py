from .self_intersection_plugin import SelfIntersectionPlugin

def classFactory(iface):
    return SelfIntersectionPlugin(iface)