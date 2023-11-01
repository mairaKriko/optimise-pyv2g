#######################################################
# 
# WaitForServiceDiscoveryReq.py
# Python implementation of the Class WaitForServiceDiscoveryReq
# Generated by Enterprise Architect
# Created on:      07-Jan-2021 12:00:30
# Original author: Fabian.Stichtenoth
# 
#######################################################
import logging

from shared.v2gMessages.msgDef.ServiceDiscoveryResType import ServiceDiscoveryResType
from shared.v2gMessages.msgDef.ServiceDiscoveryReqType import ServiceDiscoveryReqType
from shared.v2gMessages.msgDef.ServiceType import ServiceType
from shared.v2gMessages.msgDef.ChargeServiceType import ChargeServiceType
from shared.v2gMessages.msgDef.BodyBaseType import BodyBaseType
from shared.v2gMessages.msgDef.ServiceListType import ServiceListType
from shared.v2gMessages.msgDef.ServiceCategoryType import ServiceCategoryType
from shared.v2gMessages.msgDef.SupportedEnergyTransferModeType import SupportedEnergyTransferModeType
from shared.v2gMessages.msgDef.ResponseCodeType import ResponseCodeType
from shared.messageHandling.ReactionToIncomingMessage import ReactionToIncomingMessage
from shared.utils.MiscUtils import MiscUtils
from shared.enumerations.V2GMessages import V2GMessages
from secc.session.V2GCommunicationSessionSECC import V2GCommunicationSessionSECC
from secc.states.ServerState import ServerState


class WaitForServiceDiscoveryReq(ServerState):

    def __init__(self, comm_session_context: V2GCommunicationSessionSECC):
        super().__init__(comm_session_context)
        self._service_discovery_res: ServiceDiscoveryResType = ServiceDiscoveryResType()

    @staticmethod
    def __get_certificate_service() -> ServiceType:
        """
        Creates certificate_service and returns it
        :return certificate_service: ServiceType
        """
        certificate_service = ServiceType()
        certificate_service.set_free_service(True)
        certificate_service.set_service_category(ServiceCategoryType.CONTRACT_CERTIFICATE)
        certificate_service.set_service_id(2)
        certificate_service.set_service_name("Certificate")

        certificate_service.set_service_scope("certificateServiceScope")

        return certificate_service

    def get_charge_service(self) -> ChargeServiceType:
        """
        Creates charge_service and returns it
        :return charge_service: ChargeServiceType
        """
        supported_energy_transfer_modes = SupportedEnergyTransferModeType()
        supported_energy_transfer_modes.get_energy_transfermode().extend(self.get_comm_session_context().
                                                                         get_supported_energy_transfer_modes())

        charge_service = ChargeServiceType()
        charge_service.set_supported_energy_transfermode(supported_energy_transfer_modes)
        charge_service.set_service_category(ServiceCategoryType.EV_CHARGING)
        charge_service.set_service_id(1)

        charge_service.set_service_name("AC_DC_Charging")

        charge_service.set_service_scope("chargingServiceScope")

        is_charging_for_free = MiscUtils.get_property_value("charging.free")
        charge_service.set_free_service(is_charging_for_free)

        return charge_service

    def get_response_message(self) -> BodyBaseType:
        """
        Returns the _service_discovery_res
        :return _service_discovery_res: BodyBaseType
        """
        return self._service_discovery_res

    def __get_service_list(self, service_category_filter: ServiceCategoryType,
                           service_scope_filter: str) -> ServiceListType:
        """
        Creates service_list and returns it
        :param service_category_filter: ServiceCategoryType
        :param service_scope_filter: str
        :return service_list: ServiceListType
        """
        service_list = ServiceListType()

        if service_category_filter is not None:
            logging.debug("EVCC filters offered services by category: " + str(service_category_filter))

        if self.get_comm_session_context().is_tls_connection and (
                service_category_filter is not None
                and service_category_filter == ServiceCategoryType.CONTRACT_CERTIFICATE
        ) or service_category_filter is None:
            service_list.get_service().append(self.__get_certificate_service())

        return service_list

    def process_incoming_message(self, message) -> ReactionToIncomingMessage:
        """
        Initiates check if message is valid and if so acts according to it. Adds allowed requests. If something goes
        wrong, get_send_message is called based on response code FAILED_SEQUENCE_ERROR
        :param message:
        :return: get_send_message (ReactionToIncomingMessage)
        """
        if self.is_incoming_message_valid(message, ServiceDiscoveryReqType.__class__, self._service_discovery_res):
            v2g_message_req = message
            service_discovery_req: ServiceDiscoveryReqType = v2g_message_req.get_body().get_body_element().get_value()
            offered_vas_list = self.__get_service_list(service_discovery_req.get_service_category(),
                                                       service_discovery_req.get_service_scope())

            self._service_discovery_res.set_payment_option_list(self.get_comm_session_context().get_payment_options())
            self._service_discovery_res.set_charge_service(self.get_charge_service())

            if len(offered_vas_list.get_service()) > 0:
                self._service_discovery_res.set_service_list(offered_vas_list)

            self.get_comm_session_context().get_offered_services().append(self.get_charge_service())
            self.get_comm_session_context().get_offered_services().extend(offered_vas_list.get_service())

            self.get_comm_session_context().get_states().get(V2GMessages.FORK).get_allowed_requests.append(
                V2GMessages.SERVICE_DETAIL_REQ)
            self.get_comm_session_context().get_states().get(V2GMessages.FORK).get_allowed_requests.append(
                V2GMessages.PAYMENT_SERVICE_SELECTION_REQ)

        else:
            if self._service_discovery_res.get_response_code() == ResponseCodeType.FAILED_SEQUENCE_ERROR:
                response_message = self.get_sequence_error_res_message(ServiceDiscoveryResType, message)

                return self.get_send_message(response_message, V2GMessages.NONE,
                                             self._service_discovery_res.get_response_code())

            else:
                self.set_mandatory_fields_for_failed_res(self._service_discovery_res,
                                                         self._service_discovery_res.get_response_code())

        if str(self._service_discovery_res.get_response_code()).startswith("OK"):
            v2g_mes = V2GMessages.FORK

        else:
            v2g_mes = V2GMessages.NONE

        return self.get_send_message(
            self._service_discovery_res, v2g_mes, self._service_discovery_res.get_response_code())