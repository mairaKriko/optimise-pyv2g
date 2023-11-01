#######################################################
# 
# DummyBackendInterface.py
# Python implementation of the Class DummyBackendInterface
# Generated by Enterprise Architect
# Created on:      07-Jan-2021 11:47:27
# Original author: Fabian.Stichtenoth
# 
#######################################################
import logging
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from lxml import etree

from secc.session.V2GCommunicationSessionSECC import V2GCommunicationSessionSECC
from shared.v2gMessages.msgDef.PMaxScheduleEntryType import PMaxScheduleEntryType
from shared.v2gMessages.msgDef.SalesTariffEntryType import SalesTariffEntryType
from shared.v2gMessages.msgDef.CertificateChainType import CertificateChainType
from shared.v2gMessages.msgDef.SAScheduleListType import SAScheduleListType
from shared.v2gMessages.msgDef.PhysicalValueType import PhysicalValueType
from shared.v2gMessages.msgDef.UnitSymbolType import UnitSymbolType
from shared.v2gMessages.msgDef.RelativeTimeIntervalType import RelativeTimeIntervalType
from shared.v2gMessages.msgDef.EMAIDType import EMAIDType
from shared.v2gMessages.msgDef.EntryType import EntryType
from shared.enumerations.GlobalValues import GlobalValues
from shared.utils.SecurityUtils import SecurityUtils
from secc.backend.IBackendInterface import IBackendInterface


class DummyBackendInterface(IBackendInterface):

    def __init__(self, comm_session_context):
        self._comm_session_context = None
        # TODO: not sure if correct -> checking!
        self._mo_sub_ca2private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

        self.set_comm_session_context(comm_session_context)

        private_key = SecurityUtils.get_private_key("./moSubCA2.pkcs8.der")

        if private_key is None:
            logging.error("No private key available from MO Sub-CA 2 PKCS#8 file")

        else:
            self.set_mo_sub_ca2private_key(private_key)
        pass

    def __create_p_max_schedule_entry(self, multiplier: str, p_max, start, duration=None) -> PMaxScheduleEntryType:
        """
        Checks if duration is given. If not, creates PMaxSchedule without duration. If duration is given, also sets
        duration
        :param multiplier: str
        :param p_max:
        :param start:
        :param duration:
        :return p_max_schedule_entry: PMaxScheduleEntryType
        """
        if duration is None:
            p_max_value = PhysicalValueType()
            p_max_value.set_multiplier(multiplier)
            p_max_value.set_unit(UnitSymbolType.W)
            p_max_value.set_value(p_max)

            p_max_time_interval = RelativeTimeIntervalType()
            p_max_time_interval.set_start(start)

            p_max_schedule_entry = PMaxScheduleEntryType()

            # TODO: JAXBElement needs to be changed
            xml_cont: dict = vars(p_max_time_interval)

            library = etree.Element(str("urn_iso_15118_2_2013_MsgDataTypes"))

            for k, v in xml_cont.items():
                element = etree.SubElement(library, 'RelativeTimeInterval')
                element.set(str(k), v)

            p_max_schedule_entry.set_time_interval(library)
            p_max_schedule_entry.set_p_max(p_max_value)

            return p_max_schedule_entry

        elif duration is not None:
            p_max_schedule_entry = self.__create_p_max_schedule_entry(multiplier, p_max, start)
            p_max_schedule_entry.get_time_interval().get_value().set_duration(duration)

            return p_max_schedule_entry

    @staticmethod
    def __create_sales_tariff_entry(start, e_price_level) -> SalesTariffEntryType:
        """
        Creates a new sales tariff entry
        :param start:
        :param e_price_level:
        :return sales_tariff_entry: SalesTariffEntryType
        """
        sales_tariff_time_interval = RelativeTimeIntervalType()
        sales_tariff_time_interval.set_start(start)

        sales_tariff_entry = SalesTariffEntryType()

        # TODO: JAXBElement needs to be changed
        xml_cont: dict = vars(sales_tariff_time_interval)

        library = etree.Element(str("urn_iso_15118_2_2013_MsgDataTypes"))

        for k, v in xml_cont.items():
            element = etree.SubElement(library, 'RelativeTimeInterval')
            element.set(str(k), v)

        sales_tariff_entry.set_e_price_level(e_price_level)

        return sales_tariff_entry

    def get_comm_session_context(self) -> V2GCommunicationSessionSECC:
        """
        Returns the communication session context
        :return _comm_session_context: V2GCommunicationSessionSECC
        """
        return self._comm_session_context

    def get_contract_certificate_chain(self, arg) -> CertificateChainType:
        """
        If arg is of type CertificateChainType, new list with authorized emaids is created. Then checks if one of the
        entries fits onto the provided emaid and if so, returns the certificate chain. If arg is not of type
        CertificateChainType, certificate chain is returned immediately
        :param arg:
        :return: CertificateChainType
        """
        if isinstance(arg, CertificateChainType):
            provided_emaid = SecurityUtils.get_emaid(arg)

            authorized_emaids = []

            authorized_emaid1 = EMAIDType()
            authorized_emaid1.set_id("id1")
            authorized_emaid1.set_value("DE1ABCD2EF357A")

            authorized_emaid2 = EMAIDType()
            authorized_emaid2.set_id("id2")
            authorized_emaid2.set_value("DE1ABCD2EF357C")

            authorized_emaid3 = EMAIDType()
            authorized_emaid3.set_id("id2")
            authorized_emaid3.set_value("DE1230000000021")

            authorized_emaids.append(authorized_emaid1)
            authorized_emaids.append(authorized_emaid2)
            authorized_emaids.append(authorized_emaid3)

            emaid_found = False

            for emaid in authorized_emaids:
                if emaid.get_value() == provided_emaid.get_value():
                    emaid_found = True

            if emaid_found:
                return SecurityUtils.get_certificate_chain("./moCertChain.p12")

            else:
                logging.warning("EMAID '" + provided_emaid.get_value() + "' (read from common name field of contract "
                                + "certificate) is not authorized")
                return None

        else:
            return SecurityUtils.get_certificate_chain("./moCertChain.p12")

    def get_contract_certificate_private_key(self):
        """
        Provides the private key belonging to the contract certificate.
        :return private_key:
        """
        keystore = SecurityUtils.get_pkcs12keystore("./moCertChain.p12",
                                                    str(GlobalValues.PASSPHRASE_FOR_CERTIFICATES_AND_KEYS))
        private_key = SecurityUtils.get_private_key(keystore)

        if private_key is None:
            logging.error("No private key available from contract certificate keystore")

        return private_key

    def get_cps_certificate_chain(self) -> CertificateChainType:
        """
        Provides a certificate chain coming from a secondary actor with the leaf
        certificate being the provisioning certificate and possible intermediate
        certificates (sub CAs) included.
        :return: CertificateChainType
        """
        return SecurityUtils.get_certificate_chain("./cpsCertChain.p12")

    def get_cps_leaf_private_key(self):
        """
        Provides the private key belonging to the SA provisioning certificate.
        :return private_key:
        """
        keystore = SecurityUtils.get_pkcs12keystore("./cpsCertChain.p12",
                                                    str(GlobalValues.PASSPHRASE_FOR_CERTIFICATES_AND_KEYS))
        private_key = SecurityUtils.get_private_key(keystore)

        if private_key is None:
            logging.error("No private key available from Certificate Provisioning Service keystore")

        return private_key

    def get_mo_sub_ca2private_key(self):
        """
        Provides the private key belonging to the MO Sub-CA 2 certificate (signature of SalesTariff).
        :return _mo_sub_ca2private_key:
        """
        return self._mo_sub_ca2private_key

    def get_sa_schedule_list(self, max_entries_sa_schedule_tuple: int, departure_time, xml_signature_ref_elements,
                             selected_sa_schedule_tuple_id=None) -> SAScheduleListType:
        pass

    def set_comm_session_context(self, comm_session_context: V2GCommunicationSessionSECC) -> None:
        """
        Provides a reference to the current communication session for this backend interface.
        :param comm_session_context: V2GCommunicationSessionSECC
        :return: None
        """
        self._comm_session_context = comm_session_context

    def set_mo_sub_ca2private_key(self, mo_sub_ca2private_key) -> None:
        """
        Sets the private key belonging to the MO Sub-CA 2 certificate (signature of SalesTariff).
        :param mo_sub_ca2private_key:
        :return: None
        """
        self._mo_sub_ca2private_key = mo_sub_ca2private_key
