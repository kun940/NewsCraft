# -*- coding: utf-8 -*-
"""
NewsCraft 后端接口冒烟测试脚本 v2
覆盖: news 3 个 / user 5 个 / favorite 5 个 / history 4 个 = 17 个接口
- 按真实前端流程: 注册后用注册token、登录后用登录token
- 覆盖正常流程 + 异常分支（404/401/400/422）
运行: .venv\\Scripts\\python.exe api_smoke_test.py
"""
import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0
RESULTS = []


def req(method, path, body=None, token=None, expect=None, label=""):
    """发起 HTTP 请求，统计 PASS/FAIL。expect=None 表示只要非网络错误即算通过。"""
    global PASS, FAIL
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read().decode("utf-8")
    except Exception as e:
        status = 0
        raw = f"网络错误: {e}"
    try:
        j = json.loads(raw) if raw else {}
    except Exception:
        j = {"_raw": raw[:200]}

    ok = (expect is None) or (status == expect)
    if ok:
        PASS += 1
        mark = "PASS"
    else:
        FAIL += 1
        mark = "FAIL"
    brief = f"{mark} [{status}] {method} {path}"
    if label:
        brief += f"  <{label}>"
    if not ok:
        brief += f"  (期望 {expect})"
        if j:
            brief += f" | {json.dumps(j, ensure_ascii=False)[:200]}"
    print(brief)
    RESULTS.append({"mark": mark, "status": status, "method": method, "path": path,
                    "label": label, "json": j, "ok": ok})
    return status, j


def summary():
    print("\n" + "=" * 70)
    print(f"总计: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
    failed = [r for r in RESULTS if not r["ok"]]
    if failed:
        print("失败明细:")
        for r in failed:
            print(f"  - [{r['status']}] {r['method']} {r['path']} <{r['label']}>")
    print("=" * 70)
    return len(failed)


def main():
    # ---------- 1. 新闻模块（无鉴权） ----------
    print("\n【新闻模块】")
    _, j = req("GET", "/api/news/categories", expect=200, label="获取分类列表")
    cats = j.get("data", [])
    print(f"  分类数量: {len(cats)}, 样例: {json.dumps(cats[0], ensure_ascii=False, default=str) if cats else '-'}")
    first_cat = cats[0]["id"] if cats else 1

    _, j = req("GET", f"/api/news/list?categoryId={first_cat}&page=1&pageSize=5", expect=200, label="分页获取新闻列表")
    d = j.get("data", {})
    news_items = d.get("list", [])
    print(f"  新闻总数: {d.get('total')}, 本页: {len(news_items)}, hasMore: {d.get('hasMore')}")
    # 校验关键字段命名（camelCase）
    if news_items:
        item = news_items[0]
        print(f"  列表项字段: {sorted(item.keys())}")
        assert "categoryId" in item and "publishTime" in item, "列表项缺少 camelCase 字段"
    valid_news_id = news_items[0]["id"] if news_items else 1

    _, j = req("GET", f"/api/news/detail?id={valid_news_id}", expect=200, label="获取新闻详情")
    print(f"  详情标题: {(j.get('data') or {}).get('title', '')[:40]}")
    req("GET", "/api/news/detail?id=99999999", expect=404, label="不存在的新闻→404")

    # ---------- 2. 用户模块 ----------
    print("\n【用户模块】")
    uname = f"apitest_{int(time.time())}"
    pwd = "test123456"
    _, j = req("POST", "/api/user/register", {"username": uname, "password": pwd}, expect=200, label="注册新用户")
    reg_token = (j.get("data") or {}).get("token", "")
    uid = ((j.get("data") or {}).get("userInfo") or {}).get("id")
    print(f"  新用户: {uname} id={uid}")

    req("POST", "/api/user/register", {"username": uname, "password": pwd}, expect=400, label="重复用户名→400")
    req("POST", "/api/user/register", {"username": "a", "password": "123456"}, expect=422, label="用户名过短→422")
    req("POST", "/api/user/register", {"username": "validuser1", "password": "123"}, expect=422, label="密码过短→422")

    # 注册token在登录前应可用（先测，再登录——登录会覆盖token行）
    _, j = req("GET", "/api/user/info", token=reg_token, expect=200, label="注册token获取用户信息(登录前)")
    print(f"  userInfo: {json.dumps(j.get('data'), ensure_ascii=False)[:120]}")
    req("GET", "/api/user/info", expect=422, label="无token→422")
    req("GET", "/api/user/info", token="invalid_token_abc", expect=401, label="伪造token→401")

    _, j = req("POST", "/api/user/login", {"username": uname, "password": pwd}, expect=200, label="正确密码登录")
    login_token = (j.get("data") or {}).get("token", "")
    req("POST", "/api/user/login", {"username": uname, "password": "wrongpass1"}, expect=401, label="错误密码→401")
    req("POST", "/api/user/login", {"username": "no_such_user_xyz", "password": pwd}, expect=401, label="不存在用户→401")

    # 登录后: 注册token被单会话策略覆盖（设计如此），登录token可用
    req("GET", "/api/user/info", token=reg_token, expect=401, label="注册token登录后→401(单会话覆盖, 设计行为)")
    _, j = req("GET", "/api/user/info", token=login_token, expect=200, label="登录token获取用户信息")
    print(f"  登录token可用, userInfo: {json.dumps(j.get('data'), ensure_ascii=False)[:120]}")

    _, j = req("PUT", "/api/user/update", {"nickname": "冒烟测试昵称", "bio": "由自动化测试写入"},
               token=login_token, expect=200, label="更新用户资料")
    print(f"  更新后昵称: {(j.get('data') or {}).get('nickname')}")

    # ---------- 3. 收藏模块 ----------
    print("\n【收藏模块】")
    _, j = req("GET", f"/api/favorite/check?newsId={valid_news_id}", token=login_token, expect=200, label="收藏前check")
    print(f"  收藏前 isFavorite: {j.get('data', {}).get('isFavorite')}")
    _, j = req("POST", "/api/favorite/add", {"newsId": valid_news_id}, token=login_token, expect=200, label="添加收藏")
    print(f"  收藏记录: {json.dumps(j.get('data'), ensure_ascii=False, default=str)[:120]}")
    req("POST", "/api/favorite/add", {"newsId": valid_news_id}, token=login_token, expect=400, label="重复收藏→400")
    req("POST", "/api/favorite/add", {"newsId": 99999999}, token=login_token, expect=404, label="收藏不存在新闻→404")
    _, j = req("GET", f"/api/favorite/check?newsId={valid_news_id}", token=login_token, expect=200, label="收藏后check")
    print(f"  收藏后 isFavorite: {j.get('data', {}).get('isFavorite')}")
    _, j = req("GET", "/api/favorite/list?page=1&pageSize=10", token=login_token, expect=200, label="收藏列表")
    print(f"  收藏总数: {j.get('data', {}).get('total')}, 列表项字段: {sorted((j.get('data',{}).get('list') or [{}])[0].keys()) if j.get('data',{}).get('list') else '-'}")
    req("DELETE", f"/api/favorite/remove?newsId={valid_news_id}", token=login_token, expect=200, label="取消收藏")
    _, j = req("GET", "/api/favorite/list?page=1&pageSize=10", token=login_token, expect=200, label="取消后收藏列表")
    print(f"  取消后收藏总数: {j.get('data', {}).get('total')}")
    req("DELETE", "/api/favorite/clear", token=login_token, expect=200, label="清空收藏")
    req("GET", "/api/favorite/list?page=1&pageSize=10", expect=422, label="收藏列表无token→422")

    # ---------- 4. 历史模块 ----------
    print("\n【历史模块】")
    _, j = req("POST", "/api/history/add", {"newsId": valid_news_id}, token=login_token, expect=200, label="添加浏览历史")
    print(f"  历史记录: {json.dumps(j.get('data'), ensure_ascii=False, default=str)[:120]}")
    _, j = req("POST", "/api/history/add", {"newsId": valid_news_id}, token=login_token, expect=200, label="重复浏览(更新时间)")
    _, j = req("GET", "/api/history/list?page=1&pageSize=10", token=login_token, expect=200, label="历史列表")
    print(f"  历史总数: {j.get('data', {}).get('total')}")
    req("DELETE", f"/api/history/delete/{valid_news_id}", token=login_token, expect=200, label="删除单条历史")
    req("DELETE", f"/api/history/delete/{valid_news_id}", token=login_token, expect=404, label="重复删除→404")
    req("DELETE", "/api/history/clear", token=login_token, expect=200, label="清空历史")

    # ---------- 5. 修改密码 ----------
    print("\n【修改密码】")
    new_pwd = "newpass789"
    req("PUT", "/api/user/password", {"oldPassword": pwd, "newPassword": pwd}, token=login_token, expect=400, label="新旧密码相同→400")
    req("PUT", "/api/user/password", {"oldPassword": "wrong_old", "newPassword": new_pwd}, token=login_token, expect=400, label="旧密码错误→400")
    req("PUT", "/api/user/password", {"oldPassword": pwd, "newPassword": new_pwd}, token=login_token, expect=200, label="正确修改密码")
    _, j = req("POST", "/api/user/login", {"username": uname, "password": new_pwd}, expect=200, label="新密码登录")
    new_login_token = (j.get("data") or {}).get("token", "")
    req("POST", "/api/user/login", {"username": uname, "password": pwd}, expect=401, label="旧密码登录→401")
    req("PUT", "/api/user/password", {"oldPassword": new_pwd, "newPassword": pwd}, token=new_login_token, expect=200, label="用新登录token改回原密码")
    req("POST", "/api/user/login", {"username": uname, "password": pwd}, expect=200, label="恢复后原密码登录")

    # ---------- 清理测试数据 ----------
    print("\n【数据清理】")
    try:
        import asyncio
        import aiomysql

        async def cleanup():
            conn = await aiomysql.connect(host="127.0.0.1", port=3306, user="root",
                                          password="Lkj070329", db="newscraft_app", charset="utf8mb4")
            cur = await conn.cursor()
            await cur.execute("DELETE FROM `user` WHERE id=%s", (uid,))
            await conn.commit()
            affected = cur.rowcount
            conn.close()
            return affected

        affected = asyncio.run(cleanup())
        print(f"  已清理测试用户 id={uid} (删除行数: {affected})")
    except Exception as e:
        print(f"  !! 清理失败: {e} (可手动删除 user.id={uid})")

    return summary()


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
