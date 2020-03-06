# Copyright (c) 2020 fieldOfView
# MaterialCostTools is released under the terms of the AGPLv3 or higher.

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QFileDialog

import os.path
import sys
import csv
import json
from uuid import UUID

from UM.Extension import Extension
from UM.Application import Application
from UM.Logger import Logger

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

class MaterialCostTools(Extension, QObject,):
    def __init__(self, parent = None):
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._application = Application.getInstance()
        self._preferences = self._application.getPreferences()
        self._preferences.addPreference("material_cost_tools/dialog_path", "")

        self._dialog_options = QFileDialog.Options()
        if sys.platform == "linux" and "KDE_FULL_SESSION" in os.environ:
            self._dialog_options |= QFileDialog.DontUseNativeDialog


        self.addMenuItem(catalog.i18nc("@item:inmenu", "Import weights && prices..."), self.importData)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Export weights && prices..."), self.exportData)

        self.setMenuName(catalog.i18nc("@item:inmenu", "Material Cost Tools"))

    def exportData(self):
        file_name = QFileDialog.getOpenFileName(
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

        try:
            with open(file_name, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csv_writer.writerow(["guid", "weight (g)", "cost (%s)" % self._preferences.getValue("cura/currency")])

                for (guid, data) in material_settings.items():
                    csv_writer.writerow([guid, data["spool_weight"], data["spool_cost"]])
        except:
            Logger.logException("e", "Could not export settings to the selected file")
            return

    def importData(self):
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
                        header = row
                    else:
                        try:
                            (guid, weight, cost) = row
                        except:
                            Logger.log("e", "Row does not have enough data: %s" % row)
                            continue

                        try:
                            uuid = UUID(guid)
                        except:
                            Logger.log("e", "UUID is malformed: %s" % row)
                            continue

                        try:
                            material_settings[guid] = {
                                "spool_cost": float(cost),
                                "spool_weight": int(weight)
                            }
                        except:
                            Logger.log("e", "Weight or cost is malformed: %s" % row)
                            continue
        except:
            Logger.logException("e", "Could not import settings from the selected file")
            return

        self._preferences.setValue("cura/material_settings", json.dumps(material_settings))