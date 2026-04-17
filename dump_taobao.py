from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        # Find taobao page
        tb_page = None
        for ctx in browser.contexts:
            for page in ctx.pages:
                if "taobao.com" in page.url:
                    tb_page = page
                    break
            if tb_page: break
        
        if tb_page:
            print("Found Taobao page:", tb_page.url)
            html = tb_page.content()
            with open("taobao_checkout_dom.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("DOM saved to taobao_checkout_dom.html")
            
            # Let's try to find "使用新地址" and click it
            nodes = tb_page.locator('text="使用新地址"').all()
            print("Found nodes with text '使用新地址':", len(nodes))
            for i, node in enumerate(nodes):
                print(f"Node {i} HTML:", node.evaluate("node => node.outerHTML"))
            
        else:
            print("No Taobao page found.")
    except Exception as e:
        print("Error:", e)
