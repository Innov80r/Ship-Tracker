"""
Script to download real Exclusive Economic Zone (EEZ) boundaries from the MarineRegions WFS API.
"""
import asyncio
import os
import sys
import typing

import httpx


async def download_eez() -> None:
    """
    Downloads EEZ boundaries as a GeoJSON file.
    Streams the download to handle potentially large files efficiently.
    """
    url = (
        "https://geo.vliz.be/geoserver/MarineRegions/wfs"
        "?service=WFS&version=1.0.0&request=GetFeature"
        "&typeName=MarineRegions:eez&outputFormat=application/json"
    )
    output_path = os.path.join("static", "eez_boundaries.geojson")

    print("Connecting to MarineRegions WFS API using httpx...")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                total_size_str = response.headers.get("Content-Length", "0")
                total_size = int(total_size_str)
                downloaded = 0

                with open(output_path, "wb") as file:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        file.write(typing.cast(bytes, chunk))
                        downloaded += len(chunk)
                        
                        dl_mb = downloaded / 1024 / 1024
                        if total_size:
                            ts_mb = total_size / 1024 / 1024
                            sys.stdout.write(
                                f"\rDownloaded {dl_mb:.2f} MB of {ts_mb:.2f} MB"
                            )
                        else:
                            sys.stdout.write(f"\rDownloaded {dl_mb:.2f} MB")
                        sys.stdout.flush()

        print(f"\nSuccessfully downloaded real EEZ boundaries to {output_path}")
    except (httpx.RequestError, OSError) as e:
        print(f"\nDownload failed: {e}")

if __name__ == "__main__":
    asyncio.run(download_eez())
