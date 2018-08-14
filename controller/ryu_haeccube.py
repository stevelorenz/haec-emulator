#! /usr/bin/env python
# -*- coding: utf-8 -*-
#

"""
About: Ryu application for HAEC Cube Topology
       - Intra-board traffic routing:


           - Deterministic routing : XY routing
           - Adaptive routing: XY-YX routing

       - Inter-board traffic routing: TBD

Email: xianglinks@gmail.com
"""

import json
import random

from ryu.app.wsgi import ControllerBase, Response, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (CONFIG_DISPATCHER, MAIN_DISPATCHER,
                                    set_ev_cls)
from ryu.lib import dpid as dpid_lib
from ryu.lib import hub
from ryu.lib.packet import arp, ether_types, ethernet, ipv4, packet
from ryu.ofproto import ofproto_v1_3

haec_cube_instance_name = 'haec_cube_api_app'

url_mac_table = "/mactable/{dpid}"
url_ip_table = "/iptable"


class HAECCubeApp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(HAECCubeApp, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        # Table for IPs of host and the directly connected switch of this host
        # This is used by updating routing after migration
        self.ip_to_sw = {
            "10.1.1.1": "111",
            "10.2.1.1": "211",
            "10.1.2.1": "121",
            "10.2.2.1": "221",
        }

        wsgi = kwargs['wsgi']
        wsgi.register(HAECCubeController,
                      {haec_cube_instance_name: self})

    # @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    # def switch_features_handler(self, ev):
    #    datapath = ev.msg.datapath
    #    ofproto = datapath.ofproto
    #    parser = datapath.ofproto_parser

    #    match = parser.OFPMatch()
    #    actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
    #                                      ofproto.OFPCML_NO_BUFFER)]

    def _port_from_ip(self, dp, ip):
        """Get the output port of the datapath based on IP address"""
        from ryu.topology.api import get_switch, get_link, get_host
        ofp = dp.ofproto

        sw = get_switch(self, dp.id)[0]
        ports = sw.ports  # All ports of a switch
        cur_pos = dpid_lib.dpid_to_str(dp.id)[-3:]
        dst_pos = self.ip_to_sw[ip]
        self.logger.debug(
            "Current position: {}, destination position: {}".format(cur_pos,
                                                                    dst_pos))
        for i in range(3):
            ports = [p for p in ports if p.name[-3+i] == dst_pos[i]]
            if cur_pos[i] != dst_pos[i]:
                break

        if len(ports) > 0:
            hop = randon.choice(ports)
            return (hop.port_no, hop.name)
        else:
            return (None, "DROP")

    def add_flow(self, dp, src_ip, dst_ip, out_port, ifname):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        dpid = dpid_lib.dpid_to_str(dp.id)

        cookie = int(
            dpid[-3:] + "".join(src_ip.split(".")[1:]) +
            "".join(dst_ip.split(".")[1:])
        )

        match = parser.OFPMatch(
            dl_type=0x800,  # IPv4
            nw_src=src_ip,
            nw_dst=dst_ip
        )
        actions = [parser.OFPActionOutput(out_port)]

        flow = parser.OFPFlowMod(
            datapath=dp,
            command=ofp.OFPFC_ADD,
            match=match,
            cookie=cookie,  # Can be used to identify the flow
            idle_timeout=10,
            hard_timeout=0,
            priority=ofp.OFP_DEFAULT_PRIORITY,
            flags=ofp.OFPFF_SEND_FLOW_REM,
            actions=actions
        )
        dp.send_msg(flow)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):

        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        dp = msg.datapath
        parser = dp.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip = pkt.get_protocol(ipv4.ipv4)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore LLDP packet
            return

        if arp_pkt:
            out_port, _ = self._port_from_ip(dp, arp_pkt.dst_ip)
        elif ip:
            out_port, ifname = self._port_from_ip(dp, ip.dst)
            self.add_flow(dp, ip.src, ip.dst, out_port, ifname)
        else:
            self.logger.error("Unknown message: {}".format(msg))
            out_port = None
            return

        if out_port:
            actions = [parser.OFPActionOutput(out_port)]
        else:
            actions = []

        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=msg.in_port, actions=actions)
        self.send_msg(out)


class HAECCubeController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(HAECCubeController, self).__init__(req, link, data, **config)
        self.haec_cube_app = data[haec_cube_instance_name]

    @route('haeccube', url_mac_table, methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def list_mac_table(self, req, **kwargs):

        haec_cube = self.haec_cube_app
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])

        if dpid not in haec_cube.mac_to_port:
            return Response(status=404)

        mac_table = haec_cube.mac_to_port.get(dpid, {})
        body = json.dumps(mac_table)
        return Response(content_type='application/json', body=body)

    @route('haeccube', url_mac_table, methods=['PUT'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def put_mac_table(self, req, **kwargs):

        haec_cube = self.haec_cube_app
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)

        if dpid not in haec_cube.mac_to_port:
            return Response(status=404)

        try:
            mac_table = haec_cube.set_mac_to_port(dpid, new_entry)
            body = json.dumps(mac_table)
            return Response(content_type='application/json', body=body)
        except Exception as e:
            self.logger.error(e)
            return Response(status=500)

    @route('haeccube', url_ip_table, methods=['GET'])
    def list_ip_table(self, req, **kwargs):

        haec_cube = self.haec_cube_app
        body = json.dumps(haec_cube.ip_to_sw)
        return Response(content_type='application/json', body=body)

    @route('haeccube', url_ip_table, methods=['PUT'])
    def put_ip_table(self, req, **kwargs):
        """Update IP table"""
        haec_cube = self.haec_cube_app
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        pre_table = haec_cube.ip_to_sw.copy()
        for ip, sw in new_entry.iteritems():
            pre_table[ip] = sw
        if len(pre_table.values()) != len(set(pre_table.values())):
            self.logger.info("Receive an invalid ip table update.")
            return Response(status=400)
        haec_cube.ip_to_sw = pre_table

        body = json.dumps(haec_cube.ip_to_sw)
        return Response(content_type="application/json", body=body)


# General REST APIs, used for dev
app_manager.require_app('ryu.app.rest_topology')
app_manager.require_app('ryu.app.ws_topology')
app_manager.require_app('ryu.app.ofctl_rest')
