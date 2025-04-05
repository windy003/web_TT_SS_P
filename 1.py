from playwright.sync_api import sync_playwright
import time
import json
import os

def extract_article_content(url):
    """
    使用 Playwright 爬取指定头条文章链接的内容
    
    参数:
        url: 头条文章的URL
    返回:
        包含文章内容的字典
    """
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)  # 设置 headless=True 可以隐藏浏览器窗口
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 访问文章链接
            print(f"正在访问: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待文章内容加载
            page.wait_for_selector("article", state="visible", timeout=10000)
            
            # 获取文章标题
            title = page.query_selector("h1").inner_text() if page.query_selector("h1") else "无标题"
            
            # 获取文章发布时间
            publish_time = ""
            time_selectors = ["span.pubtime", "div.publication-time", "div.article-meta span"]
            for selector in time_selectors:
                element = page.query_selector(selector)
                if element:
                    publish_time = element.inner_text().strip()
                    break
                    
            # 获取文章作者
            author = ""
            author_selectors = ["div.article-meta a", "div.author", "span.name"]
            for selector in author_selectors:
                element = page.query_selector(selector)
                if element:
                    author = element.inner_text().strip()
                    break
            
            # 获取文章正文内容
            content = ""
            image_urls = []
            article_element = page.query_selector("article")
            
            if article_element:
                # 遍历 article_element 内的所有标签
                for element in article_element.query_selector_all("*"):  # 获取所有子元素
                    if element.tag_name == "p":
                        # 处理 p 标签
                        paragraph_text = element.inner_text().strip()
                        print(f"段落内容: {paragraph_text}")
                        content += paragraph_text # 将段落内容添加到正文中
                        
                    elif element.tag_name == "img":
                        # 处理 img 标签
                        img_src = element.get_attribute("src")
                        print(f"图片链接: {img_src}")
                        if img_src and not img_src.startswith("data:"):  # 过滤掉数据URI
                            image_urls.append(img_src)  # 添加图片链接到列表
                    elif element.tag_name == "section   ":
                        # 处理 section 标签
                        section_content = element.inner_text().strip()
                        print(f"段落内容: {section_content}")
                        content += section_content   # 将段落内容添加到正文中
                        
                        
            # 构建结果
            article_data = {
                "title": title,
                "author": author,
                "publish_time": publish_time,
                "content": content,
                "image_urls": image_urls,
                "url": url
            }
            
            return article_data
            
        except Exception as e:
            print(f"爬取文章时出错: {e}")
            return {
                "url": url,
                "error": str(e)
            }
        finally:
            browser.close()

def save_article(article_data, output_format="json"):
    """保存文章内容到文件"""
    timestamp = int(time.time())
    filename_base = f"article_{timestamp}"
    
    if output_format == "json":
        filename = f"{filename_base}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
    elif output_format == "txt":
        filename = f"{filename_base}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"标题: {article_data['title']}\n")
            f.write(f"作者: {article_data['author']}\n")
            f.write(f"发布时间: {article_data['publish_time']}\n")
            f.write(f"链接: {article_data['url']}\n\n")
            f.write("正文内容:\n")
            f.write(article_data['content'])
            f.write("\n\n图片链接:\n")
            for img_url in article_data['image_urls']:
                f.write(f"{img_url}\n")
    
    print(f"文章已保存为: {filename}")
    return filename

def main():
    
    url = "https://www.toutiao.com/article/7488924612110189066/?log_from=90e89e4f7547b_1743846700196"


    article_data = extract_article_content(url)
    if "error" not in article_data:
        save_article(article_data, "txt")
    else:
        print(f"爬取失败: {article_data['error']}")

if __name__ == "__main__":
    main()
