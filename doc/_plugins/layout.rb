# _plugins/implicit_layout.rb
module ImplicitLayout
  def read_yaml(*args)
    super
    self.data['layout'] ||= 'default'
  end
end

Jekyll::Page.send(:include, ImplicitLayout)
