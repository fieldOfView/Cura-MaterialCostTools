# Copyright (c) 2020 fieldOfView
# MaterialCostTools is released under the terms of the AGPLv3 or higher.

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QFileDialog, QMessageBox

import os.path
import sys
import csv
import json
import re
from uuid import UUID

from UM.Extension import Extension
from UM.Application import Application
from UM.Logger import Logger
from UM.Settings.ContainerRegistry import ContainerRegistry

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

class MaterialCostTools(Extension, QObject,):
    def __init__(self, parent = None) -> None:
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._application = Application.getInstance()
        self._preferences = self._application.getPreferences()
        self._preferences.addPreference("material_cost_tools/dialog_path", "")

        self._dialog_options = QFileDialog.Options()
        if sys.platform == "linux" and "KDE_FULL_SESSION" in os.environ:
            self._dialog_options |= QFileDialog.DontUseNativeDialog

        self.setMenuName(catalog.i18nc("@item:inmenu", "Material Cost Tools"))

        self.addMenuItem(catalog.i18nc("@item:inmenu", "Import weights && prices..."), self.importData)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Export weights && prices..."), self.exportData)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Clear all weights && prices"), self.clearData)


    def exportData(self) -> None:
        file_name = QFileDialog.getSaveFileName(
            parent = None,
            caption = catalog.i18nc("@title:window", "Save as"),
            directory = self._preferences.getValue("material_cost_tools/dialog_path"),
            filter = "CSV files (*.csv)",
            options = self._dialog_options
        )[0]

        if not file_name:
            Logger.log("d", "No file to export to selected")
            return

        self._preferences.setValue("material_cost_tools/dialog_path", os.path.dirname(file_name))

        try:
            material_settings = json.loads(self._preferences.getValue("cura/material_settings"))
        except:
            Logger.logException("e", "Could not load material settings from preferences")
            return

        materials = [
            {
                "guid": m["GUID"],
                "material": m["material"],
                "brand": m.get("brand",""),
                "name": m["name"],
                "spool_weight": material_settings.get(m["GUID"], {}).get("spool_weight", ""),
                "spool_cost": material_settings.get(m["GUID"], {}).get("spool_cost", "")
            }
            for m in ContainerRegistry.getInstance().findInstanceContainersMetadata(type = "material")
            if m["id"] == m["base_file"] and "brand" in m
        ]
        materials.sort(key = lambda k: (k["brand"], k["material"], k["name"]))

        try:
            with open(file_name, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csv_writer.writerow([
                    "guid",
                    "weight (g)",
                    "cost (%s)" % self._preferences.getValue("cura/currency"),
                    "name"
                ])

                for material in materials:
                    try:
                        csv_writer.writerow([
                            material["guid"],
                            material["spool_weight"],
                            material["spool_cost"],
                            "%s %s" % (material["brand"], material["name"])
                        ])
                    except:
                        continue
        except:
            Logger.logException("e", "Could not export settings to the selected file")
            return


    def importData(self) -> None:
        file_name = QFileDialog.getOpenFileName(
            parent = None,
            caption = catalog.i18nc("@title:window", "Open File"),
            directory = self._preferences.getValue("material_cost_tools/dialog_path"),
            filter = "CSV files (*.csv)",
            options = self._dialog_options
        )[0]

        if not file_name:
            Logger.log("d", "No file to import from selected")
            return

        self._preferences.setValue("material_cost_tools/dialog_path", os.path.dirname(file_name))

        try:
            material_settings = json.loads(self._preferences.getValue("cura/material_settings"))
        except:
            Logger.logException("e", "Could not load material settings from preferences")
            return

        try:
            with open(file_name, 'r', newline='') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                line_number = -1
                for row in csv_reader:
                    line_number += 1
                    if line_number == 0:
                        if len(row) < 3:
                            continue
                        match = re.search("cost\s\((.*)\)", row[2])
                        if not match:
                            continue

                        currency = match.group(1)

                        if currency != self._preferences.getValue("cura/currency"):

                            result = QMessageBox.question(
                                None,
                                catalog.i18nc("@title:window", "Import weights and prices"),
                                catalog.i18nc("@label",
                                    "The file contains prices specified in %s, but your Cura is configured to use %s.\nAre you sure you want to import these prices as is?" % (
                                        currency, self._preferences.getValue("cura/currency")
                                    )
                                )
                            )

                            if result == QMessageBox.No:
                                return
                    else:
                        try:
                            (guid, weight, cost) = row[0:3]
                        except:
                            Logger.log("e", "Row does not have enough data: %s" % row)
                            continue

                        try:
                            uuid = UUID(guid)
                        except:
                            Logger.log("e", "UUID is malformed: %s" % row)
                            continue

                        data = {}
                        try:
                             data["spool_cost"] = float(cost)
                        except:
                            pass
                        try:
                            data["spool_weight"] = int(weight)
                        except:
                            pass
                        if data:
                            material_settings[guid] = data
        except:
            Logger.logException("e", "Could not import settings from the selected file")
            return

        self._preferences.setValue("cura/material_settings", json.dumps(material_settings))

    def clearData(self) -> None:
        result = QMessageBox.question(
            None,
            catalog.i18nc("@title:window", "Clear weights and prices"),
            catalog.i18nc("@label", "Are you sure you want to remove the spool-weights and -prices for all materials?")
        )

        if result == QMessageBox.Yes:
            self._preferences.resetPreference("cura/material_settings")
