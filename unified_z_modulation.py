#!/usr/bin/env python3
"""
Synergistic Non-Planar Infill & Bricklayer Internal Perimeters
Copyright (c) 2023 [Your Name]
Combines square wave infill modulation with layer-shift bricklaying
"""

import re
import math
from enum import Enum
from shapely.geometry import LineString, Point


class PrintFeature(Enum):
    INFILL = 1
    INTERNAL_PERIMETER = 2
    EXTERNAL_PERIMETER = 3


class SynergisticProcessor:
    def __init__(self):
        # Square Wave Parameters
        self.infill_amplitude = 0.15  # mm Z modulation
        self.wavelength = 4.0  # mm
        self.transition_length = 0.2  # Smoothing between wave phases

        # Bricklayer Parameters
        self.bricklayer_shift = 0.1  # mm Z shift per layer group
        self.layer_group_size = 2  # Number of layers per brick

        # State tracking
        self.current_layer = 0
        self.total_z_shift = 0.0
        self.infill_pattern = "rectilinear"
        self.infill_angle = 45.0

    def process_gcode(self, input_path, output_path):
        """Main processing workflow"""
        with open(input_path, "r") as f_in, open(output_path, "w") as f_out:
            layer_lines = []
            current_feature = PrintFeature.EXTERNAL_PERIMETER

            for line in f_in:
                # Layer management
                if self._is_layer_change(line):
                    self._process_layer(layer_lines, current_feature, f_out)
                    layer_lines = []
                    self.current_layer += 1
                    continue

                # Feature detection
                current_feature = self._detect_feature(line, current_feature)
                layer_lines.append(line)

            # Process final layer
            if layer_lines:
                self._process_layer(layer_lines, current_feature, f_out)

    def _process_layer(self, lines, feature, output_handle):
        """Process a single layer with both techniques"""
        # Calculate bricklayer Z shift
        brick_z_shift = self._calculate_bricklayer_shift()

        for line in lines:
            modified_line = self._process_line(line, feature, brick_z_shift)
            output_handle.write(modified_line)

    def _process_line(self, line, feature, brick_z_shift):
        """Apply modifications based on feature type"""
        if feature == PrintFeature.INFILL:
            return self._modify_infill(line, brick_z_shift)
        elif feature == PrintFeature.INTERNAL_PERIMETER:
            return self._modify_internal_perimeter(line, brick_z_shift)
        return line

    def _modify_infill(self, line, brick_z_shift):
        """Apply square wave modulation to infill"""
        coords = self._parse_coords(line)
        if not coords:
            return line

        # Calculate wave parameters
        phase = (self.current_layer % 2) * math.pi  # Alternating phase
        wave_z = self._square_wave_z(coords["X"], coords["Y"], phase)

        # Apply combined Z modifications
        new_z = coords.get("Z", 0.0) + wave_z + brick_z_shift
        return self._update_z_value(line, new_z)

    def _modify_internal_perimeter(self, line, brick_z_shift):
        """Apply bricklayer shift to internal perimeters"""
        coords = self._parse_coords(line)
        if not coords or "Z" not in coords:
            return line

        new_z = coords["Z"] + brick_z_shift
        return self._update_z_value(line, new_z)

    def _square_wave_z(self, x, y, phase):
        """Phase-locked square wave with smoothing"""
        position = x * math.cos(phase) + y * math.sin(phase)
        normalized = (position % self.wavelength) / self.wavelength

        # Transition smoothing
        if normalized < self.transition_length / self.wavelength:
            return self.infill_amplitude * math.sin(
                normalized * math.pi / self.transition_length
            )
        elif normalized > 1 - self.transition_length / self.wavelength:
            return -self.infill_amplitude * math.sin(
                (normalized - 1) * math.pi / self.transition_length
            )

        return self.infill_amplitude if normalized < 0.5 else -self.infill_amplitude

    def _calculate_bricklayer_shift(self):
        """Determine Z shift for current layer group"""
        if self.current_layer % self.layer_group_size == 0:
            self.total_z_shift += self.bricklayer_shift
        return self.total_z_shift

    def _detect_feature(self, line, current_feature):
        """Identify G-code feature types"""
        if ";TYPE:Internal infill" in line:
            return PrintFeature.INFILL
        elif ";TYPE:Internal perimeter" in line:
            return PrintFeature.INTERNAL_PERIMETER
        elif ";TYPE:External perimeter" in line:
            return PrintFeature.EXTERNAL_PERIMETER
        return current_feature

    def _parse_coords(self, line):
        """Extract coordinates from G-code line"""
        coords = {}
        for match in re.finditer(r"([XYZ])([\d\.]+)", line):
            coords[match.group(1)] = float(match.group(2))
        return coords

    def _update_z_value(self, line, new_z):
        """Replace Z coordinate in G-code line"""
        return (
            re.sub(r"Z[\d\.]+", f"Z{new_z:.3f}", line)
            if "Z" in line
            else line.rstrip() + f" Z{new_z:.3f}\n"
        )

    def _is_layer_change(self, line):
        """Detect layer change markers"""
        return line.startswith(";LAYER:") or ";CHANGE_LAYER" in line


if __name__ == "__main__":
    processor = SynergisticProcessor()
    processor.process_gcode("input.gcode", "output.gcode")
