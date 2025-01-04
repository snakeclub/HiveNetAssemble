# 自定义构建插件示例
from HiveNetPipeline import PipelineProcesser


class ProcesserBuildDemo(PipelineProcesser):
    """
    配置文件模版生成
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildDemo'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值, 供下一个处理器处理, 异步执行的情况返回None
        """
        # 获取当前要处理的配置标识
        _current_key = context.get('current_key', 'configTemplates')  # 获取当前要处理的配置标识(从构建管道配置中获取)
        _config = context['build_config'].get(_current_key, None)  # 根据标识获取到该配置标识的具体构建配置

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 自定义的处理逻辑
        print('执行自定义处理逻辑')
        print('上下文信息-构建参数(build):', str(context['build']))
        print('上下文信息-插件配置参数(build_config):', str(_config))

        # 返回输出结果
        return input_data
