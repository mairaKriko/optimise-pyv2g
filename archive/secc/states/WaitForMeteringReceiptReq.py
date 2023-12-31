#######################################################
# 
# WaitForMeteringReceiptReq.py
# Python implementation of the Class WaitForMeteringReceiptReq
# Generated by Enterprise Architect
# Created on:      07-Jan-2021 11:58:44
# Original author: Fabian.Stichtenoth
# 
#######################################################
import logging
import numpy as np
from lxml import etree

from shared.v2gMessages.msgDef.MeteringReceiptResType import MeteringReceiptResType
from shared.v2gMessages.msgDef.BodyBaseType import BodyBaseType
from shared.v2gMessages.msgDef.SignatureType import SignatureType
from shared.v2gMessages.msgDef.MeteringReceiptReqType import MeteringReceiptReqType
from shared.v2gMessages.msgDef.MeterInfoType import MeterInfoType
from shared.v2gMessages.msgDef.ResponseCodeType import ResponseCodeType
from shared.v2gMessages.msgDef.EVSENotificationType import EVSENotificationType
from shared.v2gMessages.msgDef.CertificateChainType import CertificateChainType
from shared.v2gMessages.msgDef.V2GMessage import V2GMessage
from shared.messageHandling.ReactionToIncomingMessage import ReactionToIncomingMessage
from shared.utils.SecurityUtils import SecurityUtils
from shared.misc.State import State
from shared.misc.V2GCommunicationSession import V2GCommunicationSession
from shared.enumerations.V2GMessages import V2GMessages
from secc.session.V2GCommunicationSessionSECC import V2GCommunicationSessionSECC
from secc.states.ServerState import ServerState
from secc.states.ForkState import ForkState


class WaitForMeteringReceiptReq(ServerState):

    def __init__(self, comm_session_context: V2GCommunicationSessionSECC):
        super().__init__(comm_session_context)
        self._metering_receipt_res: MeteringReceiptResType = MeteringReceiptResType()

    def get_response_message(self) -> BodyBaseType:
        """
        Returns the _metering_receipt_res
        :return _metering_receipt_res: MeteringReceiptResType
        """
        return self._metering_receipt_res

    def __is_response_code_ok(self, metering_receipt_req: MeteringReceiptReqType, signature: SignatureType) -> bool:
        """
        Checks the metering infos and the signature. If both is ok, True is returned, otherwise False
        :param metering_receipt_req: MeteringReceiptReqType
        :param signature: SignatureType
        :return: bool
        """
        if not self.__meter_info_equals(self.get_comm_session_context().get_sent_meter_info(),
                                        metering_receipt_req.get_meterinfo()):
            logging.error("The metering values sent by the EVCC do not match the ones sent previously by the SECC. "
                          + "This is not a signature verification error.")
            self._metering_receipt_res.set_response_code(ResponseCodeType.FAILED_METERING_SIGNATURE_NOT_VALID)
            return False

        verify_xml_sig_ref_elements = {metering_receipt_req.get_id(): SecurityUtils.generate_digest(
            metering_receipt_req.get_id(), self.get_message_handler().get_jaxb_element(metering_receipt_req))}

        if not SecurityUtils.verify_signature(
                signature, self.get_message_handler().get_jaxb_element(signature.get_signed_info()),
                verify_xml_sig_ref_elements,
                self.get_comm_session_context().get_contract_signature_cert_chain().get_certificate()):
            self._metering_receipt_res.set_response_code(ResponseCodeType.FAILED_METERING_SIGNATURE_NOT_VALID)
            return False

        return True

    @staticmethod
    def __meter_info_equals(meter_info_sent_by_secc: MeterInfoType,
                            meter_info_received_from_evcc: MeterInfoType) -> bool:
        """
        Checks if meter info sent by SECC were saved and if meter info was received from EVCC. If not, False is
        returned, otherwise True
        :param meter_info_sent_by_secc: MeterInfoType
        :param meter_info_received_from_evcc: MeterInfoType
        :return: bool
        """
        if meter_info_sent_by_secc is None:
            logging.error("MeterInfo sent by SECC is not saved in session context, value is null")
            return False

        elif meter_info_received_from_evcc is None:
            logging.error("MeterInfo received from EVCC is null")
            return False

        else:
            if not (
                    meter_info_sent_by_secc.get_meter_id() == meter_info_received_from_evcc.get_meter_id()
                    or (
                            meter_info_sent_by_secc.get_meter_reading() is not None
                            and not meter_info_sent_by_secc.get_meter_reading() == meter_info_received_from_evcc
                            .get_meter_reading())
                    or (
                            meter_info_sent_by_secc.get_meter_status() is not None
                            and not meter_info_sent_by_secc.get_meter_status() == meter_info_received_from_evcc
                            .get_meter_status())
                    or (
                            meter_info_sent_by_secc.get_t_meter() is not None
                            and not meter_info_sent_by_secc.get_t_meter() == meter_info_received_from_evcc
                            .get_t_meter())
                    or (meter_info_sent_by_secc.get_sig_meter_reading() is not None and not np.array_equal(
                        meter_info_sent_by_secc.get_sig_meter_reading(),
                        meter_info_received_from_evcc.get_sig_meter_reading()))
            ):
                return False

            else:
                return True

    def process_incoming_message(self, message) -> ReactionToIncomingMessage:
        """
        Initiates check if message is valid, then checks for the response code. If everything works, get_send_message is
        returned based on FORK, otherwise based on NONE
        :param message:
        :return: get_send_message
        """
        if self.is_incoming_message_valid(message, MeteringReceiptReqType.__class__, self._metering_receipt_res):
            v2g_message_req: V2GMessage = message
            metering_receipt_req: MeteringReceiptReqType = v2g_message_req.get_body().get_body_element().get_value()

            if self.__is_response_code_ok(metering_receipt_req, v2g_message_req.get_header().get_signature()):
                self.set_evse_status(self._metering_receipt_res)

                self.get_comm_session_context().get_states().get(V2GMessages.FORK).get_allowed_requests().append(
                    V2GMessages.POWER_DELIVERY_REQ)
                self.get_comm_session_context().get_states().get(V2GMessages.FORK).get_allowed_requests().append(
                    V2GMessages.CHARGING_STATUS_REQ)
                self.get_comm_session_context().get_states().get(V2GMessages.FORK).get_allowed_requests().append(
                    V2GMessages.CURRENT_DEMAND_REQ)

                return self.get_send_message(self._metering_receipt_res, V2GMessages.FORK)

            else:
                self.set_mandatory_fields_for_failed_res(self._metering_receipt_res,
                                                         self._metering_receipt_res.get_response_code())

        else:
            if self._metering_receipt_res.get_response_code() == ResponseCodeType.FAILED_SEQUENCE_ERROR:
                response_message = self.get_sequence_error_res_message(MeteringReceiptResType(), message)
                return self.get_send_message(response_message, V2GMessages.NONE,
                                             self._metering_receipt_res.get_response_code())

            else:
                self.set_mandatory_fields_for_failed_res(self._metering_receipt_res,
                                                         self._metering_receipt_res.get_response_code())

        return self.get_send_message(self._metering_receipt_res, V2GMessages.NONE,
                                     self._metering_receipt_res.get_response_code())

    def set_evse_status(self, metering_receipt_res: MeteringReceiptResType):
        """
        Checks if AC or DC and then creates XML-element of evse status to set evse status of metering_receipt_res
        :param metering_receipt_res:
        :return: None
        """
        # TODO: JAXBElement needs to be changed
        if str(self.get_comm_session_context().get_requested_energy_transfermode()).startswith("AC"):
            xml_cont: dict = vars(
                self.get_comm_session_context().get_ac_evse_controller().get_ac_evse_status(EVSENotificationType.NONE))

            jaxb_evse_status = etree.Element(str("urn_iso_15118_2_2013_MsgDataTypes"))

            for k, v in xml_cont.items():
                element = etree.SubElement(jaxb_evse_status, 'AC_EVSEStatus')
                element.set(str(k), v)

            metering_receipt_res.set_evse_status(jaxb_evse_status)

        elif str(self.get_comm_session_context().get_requested_energy_transfermode()).startswith("DC"):
            xml_cont: dict = vars(
                self.get_comm_session_context().get_dc_evse_controller().get_dc_evse_status(EVSENotificationType.NONE))

            jaxb_ac_evse_status = etree.Element(str("urn_iso_15118_2_2013_MsgDataTypes"))

            for k, v in xml_cont.items():
                element = etree.SubElement(jaxb_ac_evse_status, 'DC_EVSEStatus')
                element.set(str(k), v)

            metering_receipt_res.set_evse_status(jaxb_ac_evse_status)

        else:
            logging.warning("RequestedEnergyTransferMode '" +
                            str(self.get_comm_session_context().get_requested_energy_transfermode()) +
                            "is neither of type AC nor DC")
