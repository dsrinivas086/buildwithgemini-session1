import asyncio
import os
import shutil
import subprocess
from playwright.async_api import async_playwright

APP_URL = "https://simple-agent-frontend-412499404791.us-east1.run.app"
OUTPUT_DIR = "/config/Desktop/Session1/simple-agent/recordings"
FINAL_WEBM_PATH = "/config/Desktop/Session1/simple-agent/agent_demo.webm"
FINAL_MP4_PATH = "/config/Desktop/Session1/simple-agent/agent_demo.mp4"

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def record_agent_demo():
    print(f"Starting Playwright video recording against {APP_URL}...")
    async with async_playwright() as p:
        # Launch browser with recording enabled
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=OUTPUT_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # Step 1: Open the travel concierge frontend
        print("Navigating to frontend...")
        await page.goto(APP_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Step 2: First prompt - "Show me curated luxury destinations in Kyoto"
        first_prompt = "Show me curated luxury destinations in Kyoto"
        print(f"Sending prompt 1: '{first_prompt}'...")
        await page.fill("#input", first_prompt)
        await page.wait_for_timeout(1000)
        await page.click("button[type='submit']")

        # Wait for agent response and A2UI card to render
        print("Waiting for agent response to prompt 1...")
        await page.wait_for_selector(".msg.agent", timeout=45000)
        await page.wait_for_timeout(6000)

        # Step 3: Second richer prompt - "Convert 500 USD to JPY for my Kyoto trip and generate a photo of a serene bamboo villa in Kyoto"
        second_prompt = "Convert 500 USD to JPY for my Kyoto trip and generate a photo of a serene bamboo villa in Kyoto"
        print(f"Sending prompt 2: '{second_prompt}'...")
        await page.fill("#input", second_prompt)
        await page.wait_for_timeout(1000)
        await page.click("button[type='submit']")

        # Wait for second agent response with tool calls, currency calculation, and image URL
        print("Waiting for agent response to prompt 2...")
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 2", timeout=60000)
        await page.wait_for_timeout(8000)

        # Scroll down to ensure both responses are cleanly visible
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(4000)

        # Close context to flush video to disk
        print("Closing browser context and saving video...")
        video_path = await page.video.path()
        await context.close()
        await browser.close()

        # Copy recorded video to final destination
        if video_path and os.path.exists(video_path):
            shutil.copy(video_path, FINAL_WEBM_PATH)
            print(f"✅ Demo video successfully recorded and saved to: {FINAL_WEBM_PATH}")
            
            # Convert to MP4 using downloaded ffmpeg binary if available
            ffmpeg_bin = "/config/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux"
            if os.path.exists(ffmpeg_bin):
                try:
                    subprocess.run([
                        ffmpeg_bin, "-y", "-i", FINAL_WEBM_PATH,
                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        FINAL_MP4_PATH
                    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print(f"✅ Converted MP4 video saved to: {FINAL_MP4_PATH}")
                except Exception as e:
                    print(f"Failed MP4 conversion: {e}")
            return FINAL_WEBM_PATH
        else:
            print("❌ Failed to locate recorded video path.")
            return None

if __name__ == "__main__":
    asyncio.run(record_agent_demo())
