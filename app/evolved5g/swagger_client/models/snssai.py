# coding: utf-8

"""
    NEF_Emulator

    No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)  # noqa: E501

    OpenAPI spec version: 0.1.0
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""

import pprint
import re  # noqa: F401

import six

class Snssai(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'sst': 'int',
        'sd': 'str'
    }

    attribute_map = {
        'sst': 'sst',
        'sd': 'sd'
    }

    def __init__(self, sst=1, sd='000001'):  # noqa: E501
        """Snssai - a model defined in Swagger"""  # noqa: E501
        self._sst = None
        self._sd = None
        self.discriminator = None
        if sst is not None:
            self.sst = sst
        if sd is not None:
            self.sd = sd

    @property
    def sst(self):
        """Gets the sst of this Snssai.  # noqa: E501

        Unsigned integer representing the Slice/Service Type. Value 0 to 127 correspond to the standardized SST range. Value 128 to 255 correspond to the Operator-specific range.  # noqa: E501

        :return: The sst of this Snssai.  # noqa: E501
        :rtype: int
        """
        return self._sst

    @sst.setter
    def sst(self, sst):
        """Sets the sst of this Snssai.

        Unsigned integer representing the Slice/Service Type. Value 0 to 127 correspond to the standardized SST range. Value 128 to 255 correspond to the Operator-specific range.  # noqa: E501

        :param sst: The sst of this Snssai.  # noqa: E501
        :type: int
        """

        self._sst = sst

    @property
    def sd(self):
        """Gets the sd of this Snssai.  # noqa: E501

        This value respresents the Slice Differentiator, in hexadecimal representation.  # noqa: E501

        :return: The sd of this Snssai.  # noqa: E501
        :rtype: str
        """
        return self._sd

    @sd.setter
    def sd(self, sd):
        """Sets the sd of this Snssai.

        This value respresents the Slice Differentiator, in hexadecimal representation.  # noqa: E501

        :param sd: The sd of this Snssai.  # noqa: E501
        :type: str
        """

        self._sd = sd

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(Snssai, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, Snssai):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other