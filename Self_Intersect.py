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
    QgsSpatialIndex
)
from qgis import processing

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
                'Invalid Features (Self-Intersections or Overlaps)',
                QgsProcessing.TypeVectorPolygon
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        
        if not input_layer:
            raise QgsProcessingException("Input layer not found!")
        
        if input_layer.geometryType() != QgsProcessing.TypeVectorPolygon:
            raise QgsProcessingException(f"Selected layer '{input_layer.name()}' is not a polygon layer!")
        
        # Preprocess with Fix Geometries
        feedback.pushInfo("Running 'Fix Geometries' to clean input layer...")
        fixed_layer = processing.run("qgis:fixgeometries", {
            'INPUT': input_layer,
            'OUTPUT': 'memory:'
        }, context=context, feedback=feedback)['OUTPUT']
        
        fields = fixed_layer.fields()
        try:
            (sink, dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                fields,
                QgsWkbTypes.Polygon,
                fixed_layer.crs()
            )
        except Exception as e:
            raise QgsProcessingException(f"Failed to create output sink: {str(e)}")
        
        # Dynamic buffer tolerance
        is_geographic = fixed_layer.crs().isGeographic()
        buffer_tolerance = 0.000001 if is_geographic else 0.1  # Adjusted for larger datasets
        
        feedback.pushInfo(f"Using buffer tolerance: {buffer_tolerance} {'degrees' if is_geographic else 'meters'}")
        
        # Build spatial index
        feedback.pushInfo("Building spatial index...")
        spatial_index = QgsSpatialIndex()
        features = {}
        for feature in fixed_layer.getFeatures():
            if feedback.isCanceled():
                break
            spatial_index.addFeature(feature)
            features[feature.id()] = feature
        
        total_features = len(features)
        batch_size = 10000
        invalid_features = []
        processed_fids = set()
        current = 0
        
        # Process features in batches
        feedback.pushInfo("Checking for self-intersections and overlaps...")
        feature_ids = list(features.keys())
        
        for i in range(0, total_features, batch_size):
            if feedback.isCanceled():
                break
            batch_ids = feature_ids[i:i + batch_size]
            batch_count = len(batch_ids)
            
            for idx, fid in enumerate(batch_ids):
                if feedback.isCanceled():
                    break
                feature = features[fid]
                geom = feature.geometry()
                
                if geom.isNull() or geom.isEmpty():
                    feedback.pushWarning(f"Feature ID {fid}: Skipped due to null or empty geometry")
                    continue
                
                # Check for self-intersections
                reason = ""
                is_invalid = False
                if not geom.isGeosValid():
                    buffered_geom = geom.buffer(buffer_tolerance, 5)
                    if buffered_geom.isEmpty() or not buffered_geom.isGeosValid():
                        is_invalid = True
                        reason = f"Self-intersection detected with buffer ({buffer_tolerance})"
                
                if is_invalid and fid not in processed_fids:
                    invalid_features.append((feature, reason))
                    processed_fids.add(fid)
                    feedback.pushInfo(f"Feature ID {fid}: Added to output ({reason})")
                
                # Check for overlaps using spatial index
                nearby_fids = spatial_index.intersects(geom.boundingBox())
                for nearby_fid in nearby_fids:
                    if nearby_fid == fid or nearby_fid in processed_fids:
                        continue
                    nearby_feature = features[nearby_fid]
                    nearby_geom = nearby_feature.geometry()
                    if nearby_geom.isNull() or nearby_geom.isEmpty():
                        continue
                    if geom.intersects(nearby_geom):
                        intersection = geom.intersection(nearby_geom)
                        if intersection.type() == QgsWkbTypes.PolygonGeometry and not intersection.isEmpty():
                            if fid not in processed_fids:
                                invalid_features.append((feature, f"Overlap with Feature ID {nearby_fid}"))
                                processed_fids.add(fid)
                                feedback.pushInfo(f"Feature ID {fid}: Added to output (Overlap with Feature ID {nearby_fid})")
                            if nearby_fid not in processed_fids:
                                invalid_features.append((nearby_feature, f"Overlap with Feature ID {fid}"))
                                processed_fids.add(nearby_fid)
                                feedback.pushInfo(f"Feature ID {nearby_fid}: Added to output (Overlap with Feature ID {fid})")
                
                current += 1
                feedback.setProgress(int(current * 100.0 / total_features))
        
        # Add invalid features to output sink
        for feature, reason in invalid_features:
            new_feature = QgsFeature(fields)
            new_feature.setGeometry(feature.geometry())
            new_feature.setAttributes(feature.attributes())
            sink.addFeature(new_feature, QgsFeatureSink.FastInsert)
        
        # Report results
        if invalid_features:
            feedback.pushInfo(f"Found {len(invalid_features)} features with self-intersections or overlaps.")
        else:
            feedback.pushInfo("No self-intersections or overlaps found.")
        
        return {self.OUTPUT: dest_id}

    def name(self):
        return 'selfintersectioncheck'

    def displayName(self):
        return 'Check Self-Intersections and Overlaps in Polygons'

    def group(self):
        return 'Vector Geometry'

    def groupId(self):
        return 'vectorgeometry'

    def createInstance(self):
        return SelfIntersectionCheck()