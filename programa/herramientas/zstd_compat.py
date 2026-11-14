"""zstd para cualquier Python: usa el módulo estándar (Python 3.14+) y, si no está, el paquete 'zstandard' (pip install zstandard).
Expone la parte de la API de compression.zstd que usa el programa."""
try:
    from compression.zstd import *            # noqa: F401,F403  (Python 3.14+)
    from compression import zstd as _z
    ZstdError, ZstdDict, ZstdDecompressor = _z.ZstdError, _z.ZstdDict, _z.ZstdDecompressor
    compress, decompress, get_frame_info = _z.compress, _z.decompress, _z.get_frame_info
except ImportError:
    import zstandard as _zs
    ZstdError = _zs.ZstdError
    class ZstdDict:
        def __init__(self, data): self._d = _zs.ZstdCompressionDict(data); self.dict_id = self._d.dict_id()
    def compress(data, level=3, zstd_dict=None):
        return _zs.ZstdCompressor(level=level, dict_data=zstd_dict._d if zstd_dict else None).compress(data)
    def decompress(data, zstd_dict=None):
        d = _zs.ZstdDecompressor(dict_data=zstd_dict._d if zstd_dict else None)
        return d.decompressobj().decompress(data)
    class _Info:
        def __init__(self, did): self.dictionary_id = did
    def get_frame_info(data): return _Info(_zs.get_frame_parameters(data).dict_id)
    class ZstdDecompressor:
        def __init__(self): self._o = _zs.ZstdDecompressor().decompressobj()
        def decompress(self, b): return self._o.decompress(b)
