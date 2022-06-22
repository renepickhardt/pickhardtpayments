class ChannelFields:
    """
    These are the values describing public data about channels that is either available
    via gossip or via the Bitcoin Blockchain. Their format is taken from the core lighting
    API. If you use a different implementation I suggest to write a wrapper around the
    `ChannelFields` and `Channel` class
    """
    SRC = 'source'
    HTLC_MINIMUM_MSAT = 'htlc_minimum_msat'
    HTLC_MAXIMUM_MSAT = 'htlc_maximum_msat'
    BASE_FEE_MSAT = 'base_fee_millisatoshi'
    ANNOUNCED = 'public'
    DEST = 'destination'
    LAST_UPDATE = 'last_update'
    FEE_RATE = 'fee_per_millionth'
    FEATURES = 'features'
    CAP = 'satoshis'
    ACTIVE = 'active'
    CLTV = 'delay'
    FLAGS = 'channel_flags'
    SHORT_CHANNEL_ID = 'short_channel_id'


class Channel:
    """
    Stores the public available information of a channel.

    The `Channel` Class is intended to be read only and internally stores
    the data from core lightning's `lightning-cli listchannels` command as a json.
    If you retrieve data from a different implementation I suggest to overload
    the constructor and transform the information into the given json format
    """

    def __init__(self, cln_jsn):
        self._cln_jsn = cln_jsn

    @property
    def cln_jsn(self):
        return self._cln_jsn

    @property
    def src(self):
        return self._cln_jsn[ChannelFields.SRC]

    @property
    def htlc_min_msat(self):
        return self._cln_jsn[ChannelFields.HTLC_MINIMUM_MSAT]

    @property
    def htlc_max_msat(self):
        return self._cln_jsn[ChannelFields.HTLC_MAXIMUM_MSAT]

    @property
    def base_fee(self):
        return self._cln_jsn[ChannelFields.BASE_FEE_MSAT]

    @property
    def is_announced(self):
        return self._cln_jsn[ChannelFields.ANNOUNCED]

    @property
    def dest(self):
        return self._cln_jsn[ChannelFields.DEST]

    @property
    def ppm(self):
        return self._cln_jsn[ChannelFields.FEE_RATE]

    @property
    def capacity(self):
        return self._cln_jsn[ChannelFields.CAP]

    @property
    def is_active(self):
        return self._cln_jsn[ChannelFields.ACTIVE]

    @property
    def cltv_delta(self):
        return self._cln_jsn[ChannelFields.CLTV]

    @property
    def flags(self):
        return self._cln_jsn[ChannelFields.FLAGS]

    @property
    def short_channel_id(self):
        return self._cln_jsn[ChannelFields.SHORT_CHANNEL_ID]

    def __str__(self):
        return str(self._cln_jsn)
