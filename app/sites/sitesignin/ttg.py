import re

import log
from app.sites.sitesignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class TTG(_ISiteSigninHandler):
    """
    TTG签到
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "totheglory.im"

    # 已签到
    _sign_regex = ['<b style="color:green;">已签到</b>']

    # 签到成功
    _success_regex = ['您已连续签到\\d+天，奖励\\d+积分，明天继续签到将获得\\d+积分奖励。']

    @classmethod
    def match(cls, url):
        """
        根据站点Url判断是否匹配当前站点签到类，大部分情况使用默认实现即可
        :param url: 站点Url
        :return: 是否匹配，如匹配则会调用该类的signin方法
        """
        return True if StringUtils.url_equal(url, cls.site_url) else False

    def signin(self, site_info: dict):
        """
        执行签到操作
        :param site_info: 站点信息，含有站点Url、站点Cookie、UA等信息
        :return: 签到结果信息
        """
        site = site_info.get("name")
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")

        # 获取页面html
        html_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=Config().get_proxies() if site_info.get("proxy") else None
                                ).get_res(url="https://totheglory.im")
        if not html_res or html_res.status_code != 200:
            log.error(f"【Sites】{site}签到失败，请检查站点连通性")
            return f'【{site}】签到失败，请检查站点连通性'
        # 判断是否已签到
        html_res.encoding = "utf-8"
        sign_status = self.__sign_in_result(html_res=html_res.text,
                                            regexs=self._sign_regex)
        if sign_status:
            log.info(f"【Sites】{site}今日已签到")
            return f'【{site}】今日已签到'

        # 获取签到参数
        signed_timestamp = re.search('(?<=signed_timestamp: ")\\d{10}', html_res.text).group()
        signed_token = re.search('(?<=signed_token: ").*(?=")', html_res.text).group()
        log.debug(f"【Sites】{site} signed_timestamp={signed_timestamp} signed_token={signed_token}")

        data = {
            'signed_timestamp': signed_timestamp,
            'signed_token': signed_token
        }
        # 签到
        sign_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=Config().get_proxies() if site_info.get("proxy") else None
                                ).post_res(url="https://totheglory.im/signed.php",
                                           data=data)
        if not sign_res or sign_res.status_code != 200:
            log.error(f"【Sites】{site}签到失败，签到接口请求失败")
            return f'【{site}】签到失败，签到接口请求失败'

        # 判断是否签到成功
        sign_status = self.__sign_in_result(html_res=sign_res.text,
                                            regexs=self._success_regex)
        if sign_status:
            log.info(f"【Sites】{site}签到成功")
            return f'【{site}】签到成功'

    def __sign_in_result(self, html_res, regexs):
        """
        判断是否签到成功
        """
        html_text = self._prepare_html_text(html_res)
        for regex in regexs:
            if re.search(str(regex), html_text):
                return True
        return False

    @staticmethod
    def _prepare_html_text(html_text):
        """
        处理掉HTML中的干扰部分
        """
        return re.sub(r"#\d+", "", re.sub(r"\d+px", "", html_text))
