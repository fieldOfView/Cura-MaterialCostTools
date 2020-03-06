# Copyright (c) 2020 Aldo Hoeben / fieldOfView
# MaterialCostTools is released under the terms of the AGPLv3 or higher.

from . import MaterialCostTools

def getMetaData():
    return {}

def register(app):
    return {"extension": MaterialCostTools.MaterialCostTools()}
