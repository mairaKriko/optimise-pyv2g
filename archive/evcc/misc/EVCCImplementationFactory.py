#######################################################
# 
# EVCCImplementationFactory.py
# Python implementation of the Class EVCCImplementationFactory
# Generated by Enterprise Architect
# Created on:      07-Jan-2021 11:07:26
# Original author: Fabian.Stichtenoth
# 
#######################################################
from evcc.evController.DummyEVController import DummyEVController
from evcc.evController.IEVController import IEVController
from evcc.session.V2GCommunicationSessionEVCC import V2GCommunicationSessionEVCC
from shared.misc.V2GImplementationFactory import V2GImplementationFactory


class EVCCImplementationFactory(V2GImplementationFactory):
    """Implementation factory for the EVCC controller
    """

    def create_ev_controller(self, comm_session_context: V2GCommunicationSessionEVCC) -> IEVController:
        """Creates the controller for the EVCC application
        :param comm_session_context: V2GCommunicationSessionEVCC
        :return IEVController:
        """
        instance: IEVController = self.build_from_properties("implementation.evcc.controller", IEVController.__class__)

        if instance is None:
            instance = DummyEVController(comm_session_context)

        return instance
