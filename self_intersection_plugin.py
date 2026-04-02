from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSink,
    QgsVectorLayer,
    QgsGeometry,
    QgsFeature,
    QgsWkbTypes,
    QgsProcessingException,
    QgsFeatureSink,
    QgsSpatialIndex,
    QgsField,
    QgsProcessingProvider,
    QgsApplication,
    QgsProcessingContext,
    QgsFillSymbol,
    QgsLinePatternFillSymbolLayer,
    QgsLineSymbol,
    QgsProject
)
from qgis import processing
from PyQt5.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon, QColor
import os


class SelfIntersectionCheck(QgsProcessingAlgorithm):
    INPUT_LAYER = 'INPUT_LAYER'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_LAYER,
                'Input Polygon Layer',
                types=[QgsProcessing.TypeVectorPolygon]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                'Self-Intersection',
                QgsProcessing.TypeVectorPolygon
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        # ✅ ORIGINAL LOGIC (UNCHANGED)
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        
        if not input_layer:
            raise QgsProcessingException("Input layer not found!")
        
        if input_layer.geometryType() != QgsProcessing.TypeVectorPolygon:
            raise QgsProcessingException(f"Selected layer '{input_layer.name()}' is not a polygon layer!")
        
        fix_result = processing.run("qgis:fixgeometries", {
            'INPUT': input_layer,
            'OUTPUT': 'memory:',
            'METHOD': 0
        }, context=context, feedback=feedback, is_child_algorithm=True)
        
        fixed_layer = fix_result['OUTPUT']
        if isinstance(fixed_layer, str):
            fixed_layer = context.getMapLayer(fixed_layer)
            if not fixed_layer or not isinstance(fixed_layer, QgsVectorLayer):
                raise QgsProcessingException("Failed to load fixed geometries layer!")
        
        fields = fixed_layer.fields()
        fields.append(QgsField("Reason", QVariant.String))
        
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Polygon,
            fixed_layer.crs()
        )
        
        is_geographic = fixed_layer.crs().isGeographic()
        buffer_tolerance = 0.0000001 if is_geographic else 0.01
        
        invalid_features = []
        processed_fids = set()
        
        features = list(fixed_layer.getFeatures())
        if not features:
            feedback.pushInfo("Finished: No features to process.")
            return {self.OUTPUT: dest_id}
        
        for feature in features:
            if feedback.isCanceled():
                break
                
            geom = feature.geometry()
            fid = feature.id()
            
            if geom.isNull() or geom.isEmpty():
                continue
            
            reason = ""
            is_invalid = False
            
            if not geom.isGeosValid():
                buffered_geom = geom.buffer(buffer_tolerance, 5)
                if buffered_geom.isEmpty() or not buffered_geom.isGeosValid():
                    is_invalid = True
                    reason = f"Self-intersection detected with positive buffer ({buffer_tolerance})"
                else:
                    buffered_geom = geom.buffer(-buffer_tolerance, 5)
                    if buffered_geom.isEmpty() or not buffered_geom.isGeosValid():
                        is_invalid = True
                        reason = f"Self-intersection detected with negative buffer ({buffer_tolerance})"
                    else:
                        reason = "Invalid geometry detected by isGeosValid, but buffer checks passed"
            
            if not is_invalid:
                buffered_geom = geom.buffer(0, 5)
                if buffered_geom.isEmpty() or not buffered_geom.isGeosValid():
                    is_invalid = True
                    reason = "Self-intersection detected with zero buffer"
            
            if is_invalid and fid not in processed_fids:
                invalid_features.append((feature, reason))
                processed_fids.add(fid)
        
        index = QgsSpatialIndex()
        feature_dict = {f.id(): f for f in features}
        for feature in features:
            if feature.geometry().isNull() or feature.geometry().isEmpty():
                continue
            index.addFeature(feature)
        
        for feature1 in features:
            if feedback.isCanceled():
                break
            geom1 = feature1.geometry()
            fid1 = feature1.id()
            if geom1.isNull() or geom1.isEmpty():
                continue
            
            candidate_ids = index.intersects(geom1.boundingBox())
            for fid2 in candidate_ids:
                if fid2 <= fid1:
                    continue
                feature2 = feature_dict[fid2]
                geom2 = feature2.geometry()
                if geom2.isNull() or geom2.isEmpty():
                    continue
                
                if geom1.intersects(geom2):
                    intersection = geom1.intersection(geom2)
                    if intersection.type() == QgsWkbTypes.PolygonGeometry and not intersection.isEmpty():
                        if fid1 not in processed_fids:
                            invalid_features.append((feature1, f"Overlap with Feature ID {fid2}"))
                            processed_fids.add(fid1)
                        if fid2 not in processed_fids:
                            invalid_features.append((feature2, f"Overlap with Feature ID {fid1}"))
                            processed_fids.add(fid2)
        
        for feature, reason in invalid_features:
            new_feature = QgsFeature(fields)
            new_feature.setGeometry(feature.geometry())
            attributes = feature.attributes()
            attributes.append(reason)
            new_feature.setAttributes(attributes)
            sink.addFeature(new_feature, QgsFeatureSink.FastInsert)
        
        feedback.pushInfo(f"Finished: Found {len(invalid_features)} features with self-intersections or overlaps.")

        # 🎨 DASHED HATCH STYLE (ONLY ADDITION)
        layer = context.getMapLayer(dest_id)
        if layer:
            symbol = QgsFillSymbol.createSimple({
                'color': '0,0,0,0',
                'outline_color': '255,0,0,255',
                'outline_width': '1.2'
            })

            line_pattern = QgsLinePatternFillSymbolLayer()
            line_pattern.setColor(QColor(0, 0, 0))
            line_pattern.setDistance(2.0)
            line_pattern.setAngle(45)

            line_pattern.setSubSymbol(
                QgsLineSymbol.createSimple({
                    'line_style': 'dash',
                    'line_width': '0.5',
                    'color': '0,0,0'
                })
            )

            symbol.appendSymbolLayer(line_pattern)

            layer.renderer().setSymbol(symbol)
            QgsProject.instance().addMapLayer(layer)

        return {self.OUTPUT: dest_id}

    def name(self):
        return 'selfintersectioncheck'

    def displayName(self):
        return 'Self Intersection Check'

    def group(self):
        return 'Vector'

    def groupId(self):
        return 'vector'

    def createInstance(self):
        return SelfIntersectionCheck()


class SelfIntersectionProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(SelfIntersectionCheck())

    def id(self):
        return 'selfintersection'

    def name(self):
        return 'Self Intersection Check'


class SelfIntersectionPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")

        self.action = QAction(QIcon(icon_path), "Self Intersection Check", self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        self.iface.addPluginToVectorMenu("&Self Intersection Check", self.action)
        self.iface.addToolBarIcon(self.action)

        self.initProcessing()

    def initProcessing(self):
        self.provider = SelfIntersectionProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        self.iface.removePluginVectorMenu("&Self Intersection Check", self.action)
        self.iface.removeToolBarIcon(self.action)

        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        processing.execAlgorithmDialog("selfintersection:selfintersectioncheck")